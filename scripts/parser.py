"""
Parser module for extracting game titles and release years from input text files.
Supports formats like:
  Ad Infinitum 2023
  Amnesia: The Bunker 2023
  Cyberpunk 2077 2020
  Half-Life 2
"""

import re
from typing import List, Optional, Dict, Any

# Matches title followed by whitespace and a 4-digit release year at the end of the line
YEAR_PATTERN = re.compile(r"^(.*?)\s+(\d{4})\s*$")

# Matches title followed by two trailing "Unknown" tokens (e.g. "XCOM: Enemy Unknown Unknown")
DOUBLE_UNKNOWN_PATTERN = re.compile(r"^(.*?\bUnknown)\s+Unknown\s*$", re.IGNORECASE)

# Matches title followed by a trailing "Unknown" token (e.g. "Targeted - 10 Days Unknown")
SINGLE_UNKNOWN_PATTERN = re.compile(r"^(.*?)\s+Unknown\s*$", re.IGNORECASE)

# Common words that precede "Unknown" in actual game titles when entered by hand without a release year
TITLE_UNKNOWN_PREFIXES = re.compile(
    r"\b(?:enemy|the|into\s+the|planet|sector|realms|lands|waters|worlds|space|"
    r"origin|identity|subject|destination|signal|code|project|mission|status|territory)\s+unknown\s*$",
    re.IGNORECASE,
)


def parse_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parses a single line into game title and release year.
    Handles 4-digit years, Playnite's 'Unknown' release year token,
    titles ending with the word 'Unknown' (both with and without a release year),
    and titles without any release year.
    Returns None if line is blank or a comment.
    """
    cleaned = line.strip()
    if not cleaned or cleaned.startswith("#"):
        return None

    # 1. Standard case: Title followed by 4-digit year (e.g. "XCOM: Enemy Unknown 2012")
    match = YEAR_PATTERN.match(cleaned)
    if match:
        title = match.group(1).strip()
        year = int(match.group(2))
        return {
            "title": title,
            "year": year,
            "raw": cleaned
        }

    # 2. Title ending in "Unknown" + Playnite's "Unknown" year (e.g. "XCOM: Enemy Unknown Unknown")
    double_unknown_match = DOUBLE_UNKNOWN_PATTERN.match(cleaned)
    if double_unknown_match:
        title = double_unknown_match.group(1).strip()
        return {
            "title": title,
            "year": None,
            "raw": cleaned
        }

    # 3. Single trailing "Unknown": distinguish hand-typed title ("XCOM: Enemy Unknown")
    #    from Playnite's missing release date ("Targeted - 10 Days Unknown")
    single_unknown_match = SINGLE_UNKNOWN_PATTERN.match(cleaned)
    if single_unknown_match and not TITLE_UNKNOWN_PREFIXES.search(cleaned):
        title = single_unknown_match.group(1).strip()
        return {
            "title": title,
            "year": None,
            "raw": cleaned
        }

    # 4. Fallback: Treat whole line as title if no release year token is at the end
    return {
        "title": cleaned,
        "year": None,
        "raw": cleaned
    }


def parse_games_file(filepath: str) -> List[Dict[str, Any]]:
    """
    Reads a text file and extracts a list of game dictionaries.
    Handles encoding issues by trying utf-8-sig, utf-8, cp1252, and latin-1.
    """
    content = ""
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            with open(filepath, "r", encoding=encoding) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue

    games = []
    for line in content.splitlines():
        parsed = parse_line(line)
        if parsed:
            games.append(parsed)

    return games
