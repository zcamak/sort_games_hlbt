import unittest
from scripts.parser import (
    parse_line,
    parse_games_file,
    parse_games_file_detailed,
    MAX_LINE_LENGTH,
    MAX_FILE_SIZE_BYTES,
)
import tempfile
import os
from unittest.mock import patch

class TestParser(unittest.TestCase):
    def test_standard_line(self):
        result = parse_line("Ad Infinitum 2023")
        self.assertEqual(result, {"title": "Ad Infinitum", "year": 2023, "raw": "Ad Infinitum 2023"})

    def test_line_with_extra_spaces(self):
        result = parse_line("   Amnesia: The Bunker    2023   ")
        self.assertEqual(result, {"title": "Amnesia: The Bunker", "year": 2023, "raw": "Amnesia: The Bunker    2023"})

    def test_title_with_number(self):
        result = parse_line("Cyberpunk 2077 2020")
        self.assertEqual(result, {"title": "Cyberpunk 2077", "year": 2020, "raw": "Cyberpunk 2077 2020"})

    def test_line_without_year(self):
        result = parse_line("Half-Life 2")
        self.assertEqual(result, {"title": "Half-Life 2", "year": None, "raw": "Half-Life 2"})

    def test_unknown_release_year_cases(self):
        # Case 1: Title ending in "Unknown" + 4-digit release date
        res1 = parse_line("XCOM: Enemy Unknown 2012")
        self.assertEqual(res1, {"title": "XCOM: Enemy Unknown", "year": 2012, "raw": "XCOM: Enemy Unknown 2012"})

        # Case 2: Title ending in "Unknown" + Playnite's "Unknown" release date
        res2 = parse_line("XCOM: Enemy Unknown Unknown")
        self.assertEqual(res2, {"title": "XCOM: Enemy Unknown", "year": None, "raw": "XCOM: Enemy Unknown Unknown"})

        # Case 3: Normal title + Playnite's "Unknown" release date
        res3 = parse_line("Targeted - 10 Days Unknown")
        self.assertEqual(res3, {"title": "Targeted - 10 Days", "year": None, "raw": "Targeted - 10 Days Unknown"})

        # Case 4: Hand-entered title ending in "Unknown" without release date
        res4 = parse_line("XCOM: Enemy Unknown")
        self.assertEqual(res4, {"title": "XCOM: Enemy Unknown", "year": None, "raw": "XCOM: Enemy Unknown"})

    def test_empty_and_comment_lines(self):
        self.assertIsNone(parse_line(""))
        self.assertIsNone(parse_line("   "))
        self.assertIsNone(parse_line("# This is a comment"))

    def test_parse_file(self):
        content = "Adios 2021\n\n# Comment\nAgony 2018\n"
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            games = parse_games_file(tmp_path)
            self.assertEqual(len(games), 2)
            self.assertEqual(games[0]["title"], "Adios")
            self.assertEqual(games[0]["year"], 2021)
            self.assertEqual(games[1]["title"], "Agony")
            self.assertEqual(games[1]["year"], 2018)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_sanity_checks_line_length_and_invalid_chars(self):
        # Line at exactly MAX_LINE_LENGTH (256 chars) is accepted
        valid_long_title = "A" * (MAX_LINE_LENGTH - 5) + " 2023"
        self.assertEqual(len(valid_long_title), MAX_LINE_LENGTH)
        self.assertIsNotNone(parse_line(valid_long_title))

        # Line exceeding MAX_LINE_LENGTH (257 chars) is rejected
        too_long_line = "A" * (MAX_LINE_LENGTH - 4) + " 2023"
        self.assertIsNone(parse_line(too_long_line))

        # Lines with control characters or null bytes are rejected
        self.assertIsNone(parse_line("Half-Life\x00 2004"))
        self.assertIsNone(parse_line("Portal\x07 2007"))

        # Lines without any alphanumeric characters in title are rejected
        self.assertIsNone(parse_line("--- 2023"))
        self.assertIsNone(parse_line("..."))

    def test_windows_and_unix_newlines(self):
        raw_bytes = b"Game One 2020\r\nGame Two 2021\nGame Three 2022\rGame Four 2023"
        with tempfile.NamedTemporaryFile("wb", delete=False) as tmp:
            tmp.write(raw_bytes)
            tmp_path = tmp.name

        try:
            games = parse_games_file(tmp_path)
            self.assertEqual(len(games), 4)
            self.assertEqual([g["title"] for g in games], ["Game One", "Game Two", "Game Three", "Game Four"])
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_binary_file_rejected(self):
        binary_data = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff"
        with tempfile.NamedTemporaryFile("wb", delete=False) as tmp:
            tmp.write(binary_data)
            tmp_path = tmp.name

        try:
            with self.assertRaises(ValueError):
                parse_games_file(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_oversized_file_rejected(self):
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp:
            tmp.write("Half-Life 2 2004\n")
            tmp_path = tmp.name

        try:
            with patch("scripts.parser.os.path.getsize", return_value=MAX_FILE_SIZE_BYTES + 1):
                with self.assertRaises(ValueError):
                    parse_games_file(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_max_games_cap_enforced(self):
        content = "\n".join(f"Game {i} 2020" for i in range(15))
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            with patch("scripts.parser.MAX_GAMES", 10):
                games = parse_games_file(tmp_path)
                self.assertEqual(len(games), 10)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_parse_games_file_detailed_warnings(self):
        too_long = "X" * 300 + " 2020"
        lines = [
            "Valid Game 2021",
            too_long,
            "--- 2022",
            "Another Valid Game 2023",
        ]
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp:
            tmp.write("\n".join(lines))
            tmp_path = tmp.name

        try:
            games, warnings = parse_games_file_detailed(tmp_path)
            self.assertEqual(len(games), 2)
            self.assertEqual([g["title"] for g in games], ["Valid Game", "Another Valid Game"])
            self.assertEqual(len(warnings), 2)
            self.assertTrue(any("exceeds the 256-character limit" in w for w in warnings))
            self.assertTrue(any("does not contain a valid alphanumeric" in w for w in warnings))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

if __name__ == "__main__":
    unittest.main()
