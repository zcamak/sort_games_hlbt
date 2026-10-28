import unittest
from scripts.time_formatter import format_duration

class TestTimeFormatter(unittest.TestCase):
    def test_minutes_only(self):
        # 55 minutes = 55/60 hours ~= 0.9167
        res = format_duration(55 / 60)
        self.assertEqual(res["display"], "55m")
        self.assertEqual(res["minutes"], 55)

    def test_hours_only(self):
        # 5 hours
        res = format_duration(5.0)
        self.assertEqual(res["display"], "5h")
        self.assertEqual(res["minutes"], 300)

    def test_hours_and_minutes(self):
        # 3h 15m = 3 + 15/60 = 3.25
        res = format_duration(3.25)
        self.assertEqual(res["display"], "3h 15m")
        self.assertEqual(res["minutes"], 195)

        # 1h 23m = 1 + 23/60 ~= 1.3833
        res = format_duration(1 + 23 / 60)
        self.assertEqual(res["display"], "1h 23m")
        self.assertEqual(res["minutes"], 83)

    def test_missing_and_zero(self):
        res_none = format_duration(None)
        self.assertEqual(res_none["display"], "--")
        self.assertEqual(res_none["minutes"], -1)

        res_zero = format_duration(0)
        self.assertEqual(res_zero["display"], "--")
        self.assertEqual(res_zero["minutes"], -1)

        res_neg = format_duration(-5)
        self.assertEqual(res_neg["display"], "--")
        self.assertEqual(res_neg["minutes"], -1)

if __name__ == "__main__":
    unittest.main()
