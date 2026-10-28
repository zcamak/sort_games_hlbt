"""
HowLongToBeat retrieval service with local JSON caching and smart candidate matching.
"""

import json
import os
import re
import time
import sys
from difflib import SequenceMatcher
from typing import List, Dict, Any, Optional, Callable
from howlongtobeatpy import HowLongToBeat

try:
    from scripts.time_formatter import format_duration
except ImportError:
    from time_formatter import format_duration

if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    APP_DIR = os.path.join(PROJECT_ROOT, "app")

os.makedirs(APP_DIR, exist_ok=True)
CACHE_FILE = os.path.join(APP_DIR, "cache.json")


# Matches an embedded parenthetical 4-digit release year in a title, e.g. "Resident Evil 4 (2005)"
PAREN_YEAR_PATTERN = re.compile(r"\(\s*(19\d{2}|20\d{2})\s*\)")

# Common edition suffixes that HowLongToBeat frequently omits from base game entries
EDITION_SUFFIX_PATTERN = re.compile(
    r"(?:\s*[:\-–—]?\s*)\b(?:"
    r"extended\s+edition|"
    r"director'?s\s+cut(?:\s+edition)?|"
    r"definitive\s+edition|"
    r"enhanced\s+edition|"
    r"complete\s+edition|"
    r"game\s+of\s+the\s+year(?:\s+edition)?|"
    r"goty(?:\s+edition)?|"
    r"ultimate\s+edition|"
    r"digital\s+deluxe\s+edition|"
    r"deluxe\s+edition|"
    r"anniversary\s+edition|"
    r"special\s+edition|"
    r"collector'?s\s+edition|"
    r"standard\s+edition|"
    r"hd\s+remaster(?:ed)?|"
    r"remastered(?:\s+edition)?"
    r")\s*$",
    re.IGNORECASE,
)


def _normalize_key(title: str, year: Optional[int]) -> str:
    cleaned_title = title.strip().lower()
    year_str = str(year) if year else ""
    return f"{cleaned_title}::{year_str}"


def _extract_paren_year(title: str) -> Optional[int]:
    """Extracts a 4-digit year inside parentheses from the title if present."""
    match = PAREN_YEAR_PATTERN.search(title)
    if match:
        return int(match.group(1))
    return None


def _normalize_title_text(title: str) -> str:
    """
    Normalizes typographic punctuation, parenthetical years, and spacing
    so HowLongToBeat's token search does not reject valid queries.
    """
    text = title.strip()
    # Normalize smart quotes / apostrophes and dashes (including Windows-1252 C1 bytes and UTF-8 replacement char)
    text = re.sub(r"(?<=\w)\ufffd(?=\w)", "'", text)
    text = text.replace("\ufffd", " ")
    text = (
        text.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\x92", "'")
        .replace("\x91", "'")
        .replace("`", "'")
        .replace("\u00b4", "'")
    )
    text = text.replace("\u201c", '"').replace("\u201d", '"').replace("\x93", '"').replace("\x94", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "-").replace("\x96", "-").replace("\x97", "-")
    # Strip embedded parenthetical year like "(2005)"
    text = PAREN_YEAR_PATTERN.sub(" ", text)
    # Normalize spaces before colons, e.g. "STASIS : BONE TOTEM" -> "STASIS: BONE TOTEM"
    text = re.sub(r"\s*:\s*", ": ", text)
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _strip_edition_suffix(title: str) -> str:
    """Removes common edition suffixes like 'Extended Edition' or 'Director's Cut Edition'."""
    stripped = EDITION_SUFFIX_PATTERN.sub("", title).strip(" :-–—")
    return stripped if stripped else title


def _generate_search_queries(title: str, year: Optional[int] = None) -> List[str]:
    """
    Generates an ordered list of search queries from most specific to broadest fallback.
    """
    queries: List[str] = []

    def _add(q: str) -> None:
        q = re.sub(r"\s+", " ", q).strip()
        if q and q not in queries:
            queries.append(q)

    norm = _normalize_title_text(title)
    _add(norm)

    # If the title contains standalone " - " (which HLTB splits into a standalone "-" search token),
    # also add a space-separated variant so HLTB matches regardless of hyphen spacing (e.g. "Targeted -10 Days").
    if " - " in norm:
        _add(norm.replace(" - ", " "))
        _add(norm.replace(" - ", " -"))

    # Strip edition suffixes (e.g. "Transient: Extended Edition" -> "Transient")
    no_edition = _strip_edition_suffix(norm)
    _add(no_edition)
    if " - " in no_edition:
        _add(no_edition.replace(" - ", " "))

    # Handle edge cases with "Unknown" when no release year was parsed
    if year is None:
        if re.search(r"\bunknown\s*$", norm, re.IGNORECASE):
            without_unknown = re.sub(r"\s+\bunknown\s*$", "", norm, flags=re.IGNORECASE).strip()
            _add(without_unknown)
            if " - " in without_unknown:
                _add(without_unknown.replace(" - ", " "))
        else:
            _add(f"{norm} Unknown")

    # Fallback to base title before colon if colon is present
    if ":" in no_edition:
        base_before_colon = no_edition.split(":")[0].strip()
        if len(base_before_colon) >= 3:
            _add(base_before_colon)

    return queries


def _calculate_title_similarity(user_title: str, candidate_name: str) -> float:
    """
    Computes case-insensitive title similarity (0.0 to 1.0) using both
    SequenceMatcher and word/token-set overlap (to handle reordered titles
    such as "Senua's Saga: Hellblade II" vs "Hellblade II: Senua's Saga").
    """
    norm_user = _normalize_title_text(user_title).lower()
    norm_cand = _normalize_title_text(candidate_name).lower()

    if not norm_user or not norm_cand:
        return 0.0

    stripped_user = _strip_edition_suffix(norm_user).lower()
    stripped_cand = _strip_edition_suffix(norm_cand).lower()

    # 1. Character sequence similarity (case-insensitive)
    seq_scores = [
        SequenceMatcher(None, norm_user, norm_cand).ratio(),
        SequenceMatcher(None, stripped_user, stripped_cand).ratio(),
    ]
    # Also compare alphanumeric-only strings (ignores hyphen/colon spacing differences)
    alnum_user = re.sub(r"[^a-z0-9]+", " ", stripped_user).strip()
    alnum_cand = re.sub(r"[^a-z0-9]+", " ", stripped_cand).strip()
    if alnum_user and alnum_cand:
        seq_scores.append(SequenceMatcher(None, alnum_user, alnum_cand).ratio())

    best_seq = max(seq_scores)

    # 2. Token-set overlap similarity (handles word-order permutations)
    tokens_user = set(re.findall(r"[a-z0-9]+", stripped_user))
    tokens_cand = set(re.findall(r"[a-z0-9]+", stripped_cand))
    token_sim = 0.0
    if tokens_user and tokens_cand:
        intersection = len(tokens_user & tokens_cand)
        token_sim = (2.0 * intersection) / (len(tokens_user) + len(tokens_cand))
        # Slight multiplier (0.98) so exact word order wins ties over reordered words
        token_sim *= 0.98

    return max(best_seq, token_sim)


class HLTBService:
    def __init__(self, cache_file: str = CACHE_FILE):
        self.cache_file = cache_file
        self.cache: Dict[str, Any] = self._load_cache()
        self.hltb = HowLongToBeat(input_minimum_similarity=0.0)

    def _load_cache(self) -> Dict[str, Any]:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self) -> None:
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save cache: {e}")

    def score_candidate(self, candidate, user_title: str, user_year: Optional[int]) -> float:
        """
        Calculates a score (0.0 to 1.0) for a search candidate based on
        case-insensitive title similarity and release year proximity.
        """
        candidate_name = getattr(candidate, "game_name", "") or ""
        custom_sim = _calculate_title_similarity(user_title, candidate_name)
        raw_sim = float(getattr(candidate, "similarity", 0.0) or 0.0)
        similarity = max(custom_sim, raw_sim)

        # Collect target years to compare against (both trailing year and embedded "(YYYY)")
        target_years: List[int] = []
        if user_year:
            try:
                target_years.append(int(user_year))
            except (ValueError, TypeError):
                pass
        paren_year = _extract_paren_year(user_title)
        if paren_year and paren_year not in target_years:
            target_years.append(paren_year)

        # Small tie-breaker bonus if candidate actually has recorded playtime data
        has_times = any(
            (getattr(candidate, field, 0) or 0) > 0
            for field in ("main_story", "main_extra", "completionist")
        )
        time_bonus = 0.02 if has_times else 0.0

        # If user did not provide any year, similarity alone guides the score
        if not target_years:
            return min(1.0, float(similarity) + time_bonus)

        candidate_year = getattr(candidate, "release_world", None)
        if candidate_year:
            try:
                cand_y = int(candidate_year)
                min_diff = min(abs(cand_y - ty) for ty in target_years)
                if min_diff == 0:
                    year_score = 1.0
                elif min_diff == 1:
                    year_score = 0.85
                elif min_diff == 2:
                    year_score = 0.6
                else:
                    year_score = 0.3
            except (ValueError, TypeError):
                year_score = 0.5
        else:
            year_score = 0.5

        # Weighted combination: 70% title similarity, 30% release year closeness
        return min(1.0, float(similarity * 0.7 + year_score * 0.3) + time_bonus)

    def fetch_game(self, title: str, year: Optional[int]) -> Dict[str, Any]:
        """
        Fetches playtime data for a single game, using cache when available.
        Automatically retries previously cached entries where 'found' was False.
        """
        cache_key = _normalize_key(title, year)
        if cache_key in self.cache and self.cache[cache_key].get("found") is True:
            return self.cache[cache_key]

        # Query HowLongToBeat
        result_data: Dict[str, Any] = {
            "user_title": title,
            "user_year": year,
            "game_name": title,
            "release_year": year,
            "game_id": None,
            "game_image_url": None,
            "game_web_link": None,
            "main_story": format_duration(None),
            "main_extra": format_duration(None),
            "completionist": format_duration(None),
            "found": False,
        }

        try:
            candidates_by_id: Dict[Any, Any] = {}
            for query in _generate_search_queries(title, year):
                results = self.hltb.search(query, similarity_case_sensitive=False)
                if results:
                    for c in results:
                        cid = getattr(c, "game_id", None) or getattr(c, "game_name", id(c))
                        if cid not in candidates_by_id:
                            candidates_by_id[cid] = c

                    # Stop querying fallbacks early if we already have a strong title match (>= 0.75)
                    best_so_far = max(
                        candidates_by_id.values(),
                        key=lambda c: _calculate_title_similarity(title, getattr(c, "game_name", "") or ""),
                    )
                    if _calculate_title_similarity(title, getattr(best_so_far, "game_name", "") or "") >= 0.75:
                        break

            if candidates_by_id:
                best_match = max(
                    candidates_by_id.values(),
                    key=lambda c: self.score_candidate(c, title, year),
                )
                eff_similarity = max(
                    _calculate_title_similarity(title, getattr(best_match, "game_name", "") or ""),
                    float(getattr(best_match, "similarity", 0.0) or 0.0),
                )

                # Check if best match is sufficiently similar (>= 0.4)
                if eff_similarity >= 0.4:
                    result_data["game_name"] = best_match.game_name
                    result_data["release_year"] = best_match.release_world or year
                    result_data["game_id"] = best_match.game_id
                    result_data["game_image_url"] = best_match.game_image_url
                    result_data["game_web_link"] = best_match.game_web_link
                    result_data["main_story"] = format_duration(best_match.main_story)
                    result_data["main_extra"] = format_duration(best_match.main_extra)
                    result_data["completionist"] = format_duration(best_match.completionist)
                    result_data["found"] = True
        except Exception as e:
            print(f"Error fetching '{title}' from HowLongToBeat: {e}")

        # Store in cache
        self.cache[cache_key] = result_data
        return result_data

    def fetch_games_list(
        self,
        games: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[int, int, Dict[str, Any]], None]] = None,
        delay_seconds: float = 0.35,
    ) -> List[Dict[str, Any]]:
        """
        Processes a list of games with progress updates and persistent caching.
        Only introduces a polite delay when actually making an external network request.
        """
        total = len(games)
        processed: List[Dict[str, Any]] = []

        for index, game in enumerate(games, start=1):
            title = game["title"]
            year = game.get("year")
            cache_key = _normalize_key(title, year)
            was_cached = cache_key in self.cache and self.cache[cache_key].get("found") is True

            game_data = self.fetch_game(title, year)
            processed.append(game_data)

            if progress_callback:
                progress_callback(index, total, game_data)

            # Save cache periodically or on finish
            if index % 5 == 0 or index == total:
                self._save_cache()

            # Add polite delay only on network calls to avoid rate limiting
            if not was_cached and index < total:
                time.sleep(delay_seconds)

        self._save_cache()
        return processed
