import sys
import unittest
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "app"))

from server import DEFAULT_SETTINGS, BadRequest, should_auto_print, validate_settings  # noqa: E402


def settings(**changes):
    return {**DEFAULT_SETTINGS, "auto_print": True, "last_auto_print": "2026-10", **changes}


class ShouldAutoPrintTest(unittest.TestCase):
    def test_waits_for_time_on_the_first(self):
        self.assertFalse(should_auto_print(datetime(2026, 11, 1, 6, 59), settings()))
        self.assertTrue(should_auto_print(datetime(2026, 11, 1, 7, 0), settings()))

    def test_catches_up_later_in_the_month(self):
        self.assertTrue(should_auto_print(datetime(2026, 11, 5, 3, 0), settings()))

    def test_prints_once_per_month(self):
        self.assertFalse(should_auto_print(datetime(2026, 11, 1, 8, 0), settings(last_auto_print="2026-11")))

    def test_off_never_prints(self):
        self.assertFalse(should_auto_print(datetime(2026, 11, 1, 8, 0), settings(auto_print=False)))


class ValidateSettingsTest(unittest.TestCase):
    def test_turning_on_skips_current_month(self):
        result = validate_settings({"auto_print": True}, DEFAULT_SETTINGS, date(2026, 11, 15))
        self.assertEqual(result["last_auto_print"], "2026-11")

    def test_strips_printer_uri(self):
        result = validate_settings({"printer_uri": " ipp://10.0.0.5/ipp/print "}, DEFAULT_SETTINGS, date.today())
        self.assertEqual(result["printer_uri"], "ipp://10.0.0.5/ipp/print")

    def test_rejects_bad_values(self):
        for changes in ({"paper_size": "legal"}, {"auto_print_time": "7am"}, {"auto_print": "yes"},
                        {"last_auto_print": "2026-11"}):
            with self.assertRaises(BadRequest):
                validate_settings(changes, DEFAULT_SETTINGS, date.today())


if __name__ == "__main__":
    unittest.main()
