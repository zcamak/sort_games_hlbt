"""
Parser module for extracting game titles and release years from input text files.
Supports formats like:
  Ad Infinitum 2023
  Amnesia: The Bunker 2023
  Cyberpunk 2077 2020
  Half-Life 2
"""

import os
import re
from typing import List, Optional, Dict, Any, Tuple

# Input sanity limits
MAX_LINE_LENGTH = 256
MAX_GAMES = 100_000
MAX_FILE_SIZE_BYTES = MAX_GAMES * MAX_LINE_LENGTH  # ~25.6 MB

# Disallowed ASCII control characters (excluding tab \x09, LF \x0a, CR \x0d)
CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

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


def _is_valid_title(title: str) -> bool:
    """Ensures a parsed title is non-empty and contains at least one letter or digit."""
    if not title or len(title) > MAX_LINE_LENGTH:
        return False
    return any(ch.isalnum() for ch in title)


def _is_binary_content(raw_bytes: bytes) -> bool:
    """
    Checks a byte buffer for null bytes or disallowed binary control characters.
    Allows UTF-16 files starting with a valid BOM (\xff\xfe or \xfe\xff).
    """
    if not raw_bytes:
        return False

    sample = raw_bytes[:8192]
    # Allow UTF-16 LE / BE with BOM
    if sample.startswith((b"\xff\xfe", b"\xfe\xff")) and not sample.startswith(b"\xff\xfe\x00\x00"):
        return False

    # Null byte in non-UTF-16 file indicates binary content
    if b"\x00" in sample:
        return True

    # Check for disallowed ASCII control bytes (0x01-0x08, 0x0B-0x0C, 0x0E-0x1F, 0x7F)
    bad_control_count = sum(
        1 for b in sample if (1 <= b <= 8) or (11 <= b <= 12) or (14 <= b <= 31) or b == 127
    )
    if bad_control_count > 0:
        return True

    return False


def parse_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parses a single line into game title and release year.
    Handles 4-digit years, Playnite's 'Unknown' release year token,
    titles ending with the word 'Unknown' (both with and without a release year),
    and titles without any release year.
    Returns None if line is blank, a comment, or fails sanity checks.
    """
    cleaned = line.strip()
    if not cleaned or cleaned.startswith("#"):
        return None

    # Sanity check: reject overly long lines or lines with binary/control characters
    if len(cleaned) > MAX_LINE_LENGTH or CONTROL_CHARS_PATTERN.search(cleaned):
        return None

    # 1. Standard case: Title followed by 4-digit year (e.g. "XCOM: Enemy Unknown 2012")
    match = YEAR_PATTERN.match(cleaned)
    if match:
        title = match.group(1).strip()
        year = int(match.group(2))
        if not _is_valid_title(title):
            return None
        return {
            "title": title,
            "year": year,
            "raw": cleaned
        }

    # 2. Title ending in "Unknown" + Playnite's "Unknown" year (e.g. "XCOM: Enemy Unknown Unknown")
    double_unknown_match = DOUBLE_UNKNOWN_PATTERN.match(cleaned)
    if double_unknown_match:
        title = double_unknown_match.group(1).strip()
        if not _is_valid_title(title):
            return None
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
        if not _is_valid_title(title):
            return None
        return {
            "title": title,
            "year": None,
            "raw": cleaned
        }

    # 4. Fallback: Treat whole line as title if no release year token is at the end
    if not _is_valid_title(cleaned):
        return None
    return {
        "title": cleaned,
        "year": None,
        "raw": cleaned
    }


def parse_games_file_detailed(filepath: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Reads a text file and returns (games, warnings).
    Enforces sanity checks on file size, binary content, line length, and total game count,
    recording human-readable reasons for any skipped lines or limits reached.
    Raises ValueError with a descriptive reason if the file itself is invalid.
    """
    file_size = os.path.getsize(filepath)
    if file_size > MAX_FILE_SIZE_BYTES:
        max_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
        actual_mb = file_size / (1024 * 1024)
        raise ValueError(
            f"File is too large ({actual_mb:.1f} MB). Maximum allowed size is {max_mb:.1f} MB."
        )

    with open(filepath, "rb") as bf:
        raw_bytes = bf.read()

    if _is_binary_content(raw_bytes):
        raise ValueError(
            "File appears to be a binary file or contains invalid control characters. "
            "Please select a plain-text (.txt) games list."
        )

    content = ""
    encodings = (
        ("utf-16", "utf-8-sig", "utf-8", "cp1252", "latin-1")
        if raw_bytes.startswith((b"\xff\xfe", b"\xfe\xff"))
        else ("utf-8-sig", "utf-8", "cp1252", "latin-1")
    )
    for encoding in encodings:
        try:
            content = raw_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    # Normalize Windows (\r\n), classic Mac (\r), and Unix (\n) line endings
    content = content.replace("\r\n", "\n").replace("\r", "\n")

    games: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for line_num, line in enumerate(content.split("\n"), start=1):
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#"):
            continue

        if len(cleaned) > MAX_LINE_LENGTH:
            warnings.append(
                f"Line {line_num} skipped: length ({len(cleaned)} chars) exceeds the {MAX_LINE_LENGTH}-character limit."
            )
            continue

        if CONTROL_CHARS_PATTERN.search(cleaned):
            warnings.append(f"Line {line_num} skipped: contains invalid control characters.")
            continue

        parsed = parse_line(cleaned)
        if not parsed:
            warnings.append(
                f"Line {line_num} skipped ('{cleaned[:40]}'): does not contain a valid alphanumeric game title."
            )
            continue

        games.append(parsed)
        if len(games) >= MAX_GAMES:
            warnings.append(
                f"Reached maximum limit of {MAX_GAMES:,} games; remaining lines in file were ignored."
            )
            break

    return games, warnings


def parse_games_file(filepath: str) -> List[Dict[str, Any]]:
    """
    Reads a text file and extracts a list of game dictionaries.
    Enforces sanity checks on file size, binary content, line length, and total game count.
    Handles both Windows (CRLF) and Unix (LF) newlines across common encodings.
    """
    games, _ = parse_games_file_detailed(filepath)
    return games
