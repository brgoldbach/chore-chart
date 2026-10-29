import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "app"))

from motifs import THEMES, easter_date, jack_o_lantern, theme_for  # noqa: E402

MARGIN = 0.5


class EasterTest(unittest.TestCase):
    def test_known_dates(self):
        self.assertEqual([easter_date(year) for year in (2024, 2025, 2026, 2027, 2028)],
                         [date(2024, 3, 31), date(2025, 4, 20), date(2026, 4, 5), date(2027, 3, 28),
                          date(2028, 4, 16)])


class ThemeTest(unittest.TestCase):
    def test_seasons_and_holidays(self):
        themes = [theme_for(date(2026, month, 1)) for month in range(1, 13)]
        self.assertEqual(themes, ["winter", "winter", "spring", "easter", "spring", "summer",
                                  "july4", "summer", "fall", "halloween", "thanksgiving", "christmas"])

    def test_easter_moves_with_the_date(self):
        # Easter 2027 is March 28, so March gets the Easter theme and April is spring.
        self.assertEqual((theme_for(date(2027, 3, 1)), theme_for(date(2027, 4, 1))), ("easter", "spring"))

    def test_jack_o_lantern_stays_upright(self):
        # Every piece carries the pumpkin's center as its pivot, so the sheet moves it instead of flipping it.
        self.assertEqual({shape[3] for shape in jack_o_lantern((0.36, 0.37), 0.26)}, {(0.36, 0.37)})

    def test_every_theme_stays_in_the_printable_margin(self):
        # Every point is at least 0.2 in from the paper edge, and outside the content area.
        for name, shapes in THEMES.items():
            with self.subTest(name):
                points = [point for shape in shapes for point in shape[2]]
                self.assertTrue(all(0.2 <= min(u, v) < MARGIN for u, v in points))


if __name__ == "__main__":
    unittest.main()
