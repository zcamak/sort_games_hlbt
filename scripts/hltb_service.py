"""
HowLongToBeat retrieval service with local JSON caching and smart candidate matching.
"""

import json
import os
import time
import sys
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


def _normalize_key(title: str, year: Optional[int]) -> str:
    cleaned_title = title.strip().lower()
    year_str = str(year) if year else ""
    return f"{cleaned_title}::{year_str}"


class HLTBService:
    def __init__(self, cache_file: str = CACHE_FILE):
        self.cache_file = cache_file
        self.cache: Dict[str, Any] = self._load_cache()
        self.hltb = HowLongToBeat()

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
        title similarity and release year proximity.
        """
        similarity = getattr(candidate, "similarity", 0.0) or 0.0
        
        # If user did not provide a year, similarity alone guides the score
        if not user_year:
            return float(similarity)

        candidate_year = getattr(candidate, "release_world", None)
        if candidate_year:
            try:
                candidate_year = int(candidate_year)
                diff = abs(candidate_year - int(user_year))
                if diff == 0:
                    year_score = 1.0
                elif diff == 1:
                    year_score = 0.85
                elif diff == 2:
                    year_score = 0.6
                else:
                    year_score = 0.3
            except (ValueError, TypeError):
                year_score = 0.5
        else:
            year_score = 0.5

        # Weighted combination: 70% title similarity, 30% release year closeness
        return float(similarity * 0.7 + year_score * 0.3)

    def fetch_game(self, title: str, year: Optional[int]) -> Dict[str, Any]:
        """
        Fetches playtime data for a single game, using cache when available.
        """
        cache_key = _normalize_key(title, year)
        if cache_key in self.cache:
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
            results = self.hltb.search(title)
            if results and len(results) > 0:
                best_match = max(results, key=lambda c: self.score_candidate(c, title, year))
                
                # Check if best match is sufficiently similar (> 0.4)
                if getattr(best_match, "similarity", 0.0) >= 0.4:
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
            was_cached = cache_key in self.cache

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
