import unittest
import os
import tempfile
import json
from scripts.hltb_service import HLTBService, _normalize_key

class DummyCandidate:
    def __init__(self, name, year, similarity):
        self.game_name = name
        self.release_world = year
        self.similarity = similarity

class TestHLTBService(unittest.TestCase):
    def test_normalize_key(self):
        self.assertEqual(_normalize_key("  Ad Infinitum  ", 2023), "ad infinitum::2023")
        self.assertEqual(_normalize_key("Half-Life", None), "half-life::")

    def test_score_candidate(self):
        service = HLTBService(cache_file="dummy_cache.json")
        c1 = DummyCandidate("Game A", 2023, 1.0)
        c2 = DummyCandidate("Game A", 2010, 1.0)
        score1 = service.score_candidate(c1, "Game A", 2023)
        score2 = service.score_candidate(c2, "Game A", 2023)
        self.assertGreater(score1, score2)

    def test_cache_persistence(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            service = HLTBService(cache_file=tmp_path)
            service.cache["test::2020"] = {"game_name": "Test", "found": True}
            service._save_cache()

            # Reload
            service2 = HLTBService(cache_file=tmp_path)
            self.assertIn("test::2020", service2.cache)
            self.assertEqual(service2.cache["test::2020"]["game_name"], "Test")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

if __name__ == "__main__":
    unittest.main()
