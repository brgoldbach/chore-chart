import json
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parents[1] / "app"))

import server  # noqa: E402
from server import (DEFAULT_SETTINGS, BadRequest, load_printout, should_auto_print, validate_printout,  # noqa: E402
                    validate_settings)
from sheet import PRINTOUT_DEFAULTS  # noqa: E402

NO_LAYOUTS = {"options": PRINTOUT_DEFAULTS, "saved": [], "colors": {}}
OWNERS = ["Bruno", "Bella"]


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


class ValidatePrintoutTest(unittest.TestCase):
    def test_merges_option_changes(self):
        result = validate_printout({"options": {"style": "grid"}}, NO_LAYOUTS, OWNERS)
        self.assertEqual(result, {**NO_LAYOUTS, "options": {**PRINTOUT_DEFAULTS, "style": "grid"}})

    def test_saved_layout_gets_trimmed_name_and_every_option(self):
        result = validate_printout({"saved": [{"name": " Fridge ", "options": {"color": "gray"}}]}, NO_LAYOUTS,
                                   OWNERS)
        self.assertEqual(result["saved"], [{"name": "Fridge", "options": {**PRINTOUT_DEFAULTS, "color": "gray"}}])

    def test_rejects_bad_names(self):
        for names in ([""], ["x" * 31], ["Fridge", "fridge"], ["week GRID"]):
            saved = [{"name": name, "options": {}} for name in names]
            with self.subTest(names=names), self.assertRaises(BadRequest):
                validate_printout({"saved": saved}, NO_LAYOUTS, OWNERS)

    def test_rejects_bad_shapes_and_options(self):
        for changes in ([], {"layouts": []}, {"options": []}, {"saved": [{"name": "A"}]},
                        {"options": {"write_in_lines": True}}, {"colors": []}, {"colors": {"Bruno": "pink"}}):
            with self.subTest(changes=changes), self.assertRaises(BadRequest):
                validate_printout(changes, NO_LAYOUTS, OWNERS)

    def test_colors_of_people_who_left_drop_out(self):
        result = validate_printout({"colors": {"Bruno": "teal", "Gone": "plum"}}, NO_LAYOUTS, OWNERS)
        self.assertEqual(result["colors"], {"Bruno": "teal"})


class LoadPrintoutTest(unittest.TestCase):
    def load(self, stored=None):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "printout.json"
            if stored is not None:
                path.write_text(json.dumps(stored))
            with mock.patch.object(server, "PRINTOUT_FILE", path):
                return load_printout()

    def test_no_file_gives_the_defaults(self):
        self.assertEqual(self.load(), NO_LAYOUTS)

    def test_old_files_get_new_options_and_drop_removed_ones(self):
        result = self.load({"options": {"style": "grid", "removed": 1},
                            "saved": [{"name": "Old", "options": {"color": "gray"}}],
                            "colors": {"Bruno": "teal", "Bella": "removed"}})
        self.assertEqual(result, {"options": {**PRINTOUT_DEFAULTS, "style": "grid"},
                                  "saved": [{"name": "Old", "options": {**PRINTOUT_DEFAULTS, "color": "gray"}}],
                                  "colors": {"Bruno": "teal"}})


if __name__ == "__main__":
    unittest.main()
