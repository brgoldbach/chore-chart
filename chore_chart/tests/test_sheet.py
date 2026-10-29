import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "app"))

from sheet import corner_points, lines_for, render  # noqa: E402


def section(name, count):
    rows = [{"id": name, "name": f"{name} {i}", "note": "", "every": "", "boxes": [{"key": "k", "day": None, "done": False}]}
            for i in range(count)]
    return {"kind": "owner", "name": name, "title": name, "label": name, "minutes": 0, "rows": rows}


def rendered(sections):
    sheet = render(date(2026, 11, 1), sections, [], "letter")
    sheet.output()  # also releases the font files
    return sheet


class LayoutTest(unittest.TestCase):
    def test_two_slots_per_line_including_blank_rows(self):
        # 4 blanks: 0 chores take 2 lines; 3 chores and 5 blanks take 4; 4 chores and 4 blanks take 4.
        self.assertEqual([lines_for(section("A", count)) for count in (0, 3, 4)], [2, 4, 4])

    def test_household_stays_full_size_on_one_page(self):
        sheet = rendered([section("Bruno", 5), section("Bella", 8), section("Ada", 3)])
        self.assertEqual((sheet.scale, sheet.pages_count), (1, 1))

    def test_big_month_shrinks_onto_one_page(self):
        sheet = rendered([section(name, 20) for name in ("Bruno", "Bella", "Ada")])
        self.assertLess(sheet.scale, 1)
        self.assertEqual(sheet.pages_count, 1)

    def test_corner_shapes_mirror_but_upright_ones_move(self):
        # A stem above the center: mirrored into the bottom-right corner it points down; upright it stays on top.
        def rounded(points):
            return [(round(x, 2), round(y, 2)) for x, y in points]

        stem_and_center = [(0.36, 0.25), (0.36, 0.37)]
        self.assertEqual(rounded(corner_points(stem_and_center, None, True, True, 8.5, 11)),
                         [(8.14, 10.75), (8.14, 10.63)])
        self.assertEqual(rounded(corner_points(stem_and_center, (0.36, 0.37), True, True, 8.5, 11)),
                         [(8.14, 10.51), (8.14, 10.63)])

    def test_overflow_continues_on_next_page(self):
        self.assertEqual(rendered([section(name, 40) for name in ("Bruno", "Bella", "Ada")]).pages_count, 2)


if __name__ == "__main__":
    unittest.main()
