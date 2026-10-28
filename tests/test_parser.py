import unittest
from scripts.parser import parse_line, parse_games_file
import tempfile
import os

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

if __name__ == "__main__":
    unittest.main()
