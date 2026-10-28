import unittest
import os
import tempfile
import json
from scripts.hltb_service import (
    HLTBService,
    _normalize_key,
    _normalize_title_text,
    _strip_edition_suffix,
    _generate_search_queries,
    _calculate_title_similarity,
)

class DummyCandidate:
    def __init__(self, name, year, similarity, main_story=10.0):
        self.game_name = name
        self.release_world = year
        self.similarity = similarity
        self.main_story = main_story
        self.main_extra = 0.0
        self.completionist = 0.0

class TestHLTBService(unittest.TestCase):
    def test_normalize_key(self):
        self.assertEqual(_normalize_key("  Ad Infinitum  ", 2023), "ad infinitum::2023")
        self.assertEqual(_normalize_key("Half-Life", None), "half-life::")

    def test_title_normalization_and_editions(self):
        self.assertEqual(
            _normalize_title_text("Senua\u2019s Saga: Hellblade II"),
            "Senua's Saga: Hellblade II",
        )
        self.assertEqual(
            _normalize_title_text("Resident Evil 4 (2005)"),
            "Resident Evil 4",
        )
        self.assertEqual(
            _normalize_title_text("STASIS : BONE TOTEM"),
            "STASIS: BONE TOTEM",
        )
        self.assertEqual(
            _strip_edition_suffix("Transient: Extended Edition"),
            "Transient",
        )
        self.assertEqual(
            _strip_edition_suffix("Darkness Within 2: The Dark Lineage Director's Cut Edition"),
            "Darkness Within 2: The Dark Lineage",
        )

    def test_case_and_word_order_similarity(self):
        # All-caps vs Title Case
        self.assertGreaterEqual(_calculate_title_similarity("CHORDOSIS", "Chordosis"), 0.99)
        self.assertGreaterEqual(_calculate_title_similarity("SIMULACRA 2", "Simulacra 2"), 0.99)
        # Reordered title words with smart apostrophe
        self.assertGreaterEqual(
            _calculate_title_similarity("Senua\u2019s Saga: Hellblade II", "Hellblade II: Senua's Saga"),
            0.95,
        )

    def test_score_candidate_and_paren_year(self):
        service = HLTBService(cache_file="dummy_cache.json")
        c1 = DummyCandidate("Game A", 2023, 1.0)
        c2 = DummyCandidate("Game A", 2010, 1.0)
        score1 = service.score_candidate(c1, "Game A", 2023)
        score2 = service.score_candidate(c2, "Game A", 2023)
        self.assertGreater(score1, score2)

        # Parenthetical year in title ("Resident Evil 4 (2005) 2011") should prefer 2005 over 2023 remake
        re4_2005 = DummyCandidate("Resident Evil 4", 2005, 0.8)
        re4_2023 = DummyCandidate("Resident Evil 4", 2023, 0.8)
        self.assertGreater(
            service.score_candidate(re4_2005, "Resident Evil 4 (2005)", 2011),
            service.score_candidate(re4_2023, "Resident Evil 4 (2005)", 2011),
        )

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
