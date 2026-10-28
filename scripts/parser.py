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


def parse_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parses a single line into game title and release year.
    Returns None if line is blank or a comment.
    """
    cleaned = line.strip()
    if not cleaned or cleaned.startswith("#"):
        return None

    match = YEAR_PATTERN.match(cleaned)
    if match:
        title = match.group(1).strip()
        year = int(match.group(2))
        return {
            "title": title,
            "year": year,
            "raw": cleaned
        }
    else:
        # Fallback: Treat whole line as title if no 4-digit year detected at the end
        return {
            "title": cleaned,
            "year": None,
            "raw": cleaned
        }


def parse_games_file(filepath: str) -> List[Dict[str, Any]]:
    """
    Reads a text file and extracts a list of game dictionaries.
    Handles encoding issues by trying utf-8, utf-8-sig, and latin-1.
    """
    content = ""
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
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
