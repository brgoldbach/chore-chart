import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "app"))

from sheet import (PERSON_COLORS, PRESETS, PRINTOUT_DEFAULTS, PRINTOUT_OPTIONS, CardSheet,  # noqa: E402
                   clean_options, corner_points, printed_sections, render, week_spans)

NOVEMBER = date(2026, 11, 1)


def row(name, dates=0, note="", done=False):
    boxes = ([{"key": f"k{index}", "day": 1 + 7 * index, "done": done} for index in range(dates)]
             or [{"key": "k", "day": None, "done": done}])
    return {"id": name, "name": name, "note": note, "every": "", "boxes": boxes}


def section(name, count=0, kind="owner", minutes=0, rows=()):
    rows = list(rows) + [row(f"{name} chore {index}") for index in range(count)]
    return {"kind": kind, "name": name, "title": name, "label": name, "minutes": minutes, "rows": rows}


def household(count):
    return [section(name, count) for name in ("Bruno", "Bella", "Ada")] + [section("Shared", kind="shared")]


def rendered(sections, **changes):
    sheet = render(NOVEMBER, sections, ["Dishes", "Counters"], "letter", clean_options(changes), {})
    sheet.output()  # also releases the font files
    return sheet


class StyleTest(unittest.TestCase):
    def test_household_fits_one_page_at_full_size_or_larger(self):
        for style in ("cards", "grid"):
            with self.subTest(style=style):
                sheet = rendered(household(4), style=style)
                self.assertEqual(sheet.pages_count, 1)
                self.assertGreaterEqual(sheet.scale, 1)

    def test_full_month_shrinks_onto_one_page(self):
        # One-page capacity for 3 people: about 14 chores each in Cards, 7 in Week grid.
        for style, count in (("cards", 12), ("grid", 5)):
            with self.subTest(style=style):
                sheet = rendered(household(count), style=style, fit_page=False)
                self.assertEqual(sheet.pages_count, 1)
                self.assertLess(sheet.scale, 1)

    def test_overflow_continues_on_next_page(self):
        for style in ("cards", "grid"):
            with self.subTest(style=style):
                self.assertGreater(rendered(household(40), style=style, fit_page=False).pages_count, 1)


class FitTest(unittest.TestCase):
    def test_a_month_that_fits_gives_up_nothing(self):
        self.assertEqual(rendered(household(4)).fitted, [])

    def test_too_full_a_month_gives_up_write_in_lines_first(self):
        # 16 chores each, with 2 write-in lines, run past one page at 8 pt; without them they fit.
        self.assertEqual(rendered(household(16), fit_page=False).pages_count, 2)
        sheet = rendered(household(16))
        self.assertEqual((sheet.pages_count, sheet.fitted), (1, ["0 write-in lines"]))

    def test_last_resort_is_smaller_text(self):
        sheet = rendered(household(24))
        self.assertEqual(sheet.pages_count, 1)
        self.assertIn("smaller text", sheet.fitted)


class CardsTest(unittest.TestCase):
    def cards(self, sections, **changes):
        options = clean_options(changes)
        sheet = CardSheet(NOVEMBER, printed_sections(sections, options, {}), [], "letter", options)

        def finish():
            sheet.draw()
            sheet.output()  # also releases the font files

        self.addCleanup(finish)
        return sheet

    def test_rows_of_cards_side_by_side_line_up(self):
        # Day numbers and notes fit in the row, so every line has one height and the cards end level.
        laundry, windows = row("Laundry", dates=4), row("Windows", note="Inside and out")
        sheet = self.cards([section("Bruno", 6), section("Bella", rows=[laundry, windows])])
        first = sheet.card_rows()[0]
        for card in first:
            self.assertEqual({sheet.line_h(card, line) for line in card["lines"]}, {sheet.rh})
            self.assertAlmostEqual(sheet.card_h(card), card["height"])

    def test_last_row_that_is_not_full_spans_the_page(self):
        sheet = self.cards([section("Bruno", 2), section("Bella", 2), section("Shared", 2, kind="shared")])
        last = sheet.card_rows()[1]
        self.assertEqual(len(last), 1)
        self.assertAlmostEqual(last[0]["width"], sheet.epw)
        self.assertEqual(last[0]["columns"], 2)

    def test_narrow_card_puts_many_dates_under_the_name(self):
        laundry = row("Fold and put away the laundry", dates=5)
        sheet = self.cards([section("Bruno", rows=[laundry]), section("Bella"), section("Ada")], cards_per_row=3)
        card = sheet.card_rows()[0][0]
        self.assertFalse(sheet.boxes_fit(laundry, sheet.slot_w(card)))
        self.assertEqual(sheet.slot_h(laundry, sheet.slot_w(card)), 2 * sheet.rh)


class GridTest(unittest.TestCase):
    def test_a_column_for_each_seven_days(self):
        self.assertEqual(week_spans(NOVEMBER), [(1, 7), (8, 14), (15, 21), (22, 28), (29, 30)])
        self.assertEqual(week_spans(date(2027, 2, 1)), [(1, 7), (8, 14), (15, 21), (22, 28)])


class OptionsTest(unittest.TestCase):
    def test_hide_empty_and_times_off(self):
        sections = [section("Bruno", 2, minutes=30), section("Bella"), section("Shared", kind="shared")]
        printed = printed_sections(sections, clean_options({"show_empty": False, "show_times": False}), {})
        self.assertEqual([(each["title"], each["minutes"]) for each in printed], [("Bruno", 0)])

    def test_chosen_and_automatic_colors_never_clash(self):
        # Ada chose teal, so the automatic colors start at plum. Bruno is hidden but still takes plum.
        sections = [section("Bruno"), section("Bella", 2), section("Ada", 1), section("Shared", 1, kind="shared")]
        printed = printed_sections(sections, clean_options({"show_empty": False}), {"Ada": "teal"})
        self.assertEqual([(each["title"], each["color"]) for each in printed],
                         [("Bella", PERSON_COLORS["green"]), ("Ada", PERSON_COLORS["teal"]), ("Shared", None)])

    def test_every_option_value_renders_in_both_styles(self):
        sections = [section("Bruno", 2, rows=[row("Laundry", dates=4, done=True), row("Windows", note="Inside")]),
                    section("Bella"), section("Shared", 1, kind="shared")]
        for name, (default, allowed) in PRINTOUT_OPTIONS.items():
            values = allowed if allowed is not None else [not default] if isinstance(default, bool) else ["Our house"]
            for style in ("cards", "grid"):
                for value in values:
                    with self.subTest(style=style, option=name, value=value):
                        self.assertGreaterEqual(rendered(sections, **{"style": style, name: value}).pages_count, 1)

    def test_built_in_layouts_are_complete_and_valid(self):
        for name, options in PRESETS.items():
            with self.subTest(layout=name):
                self.assertEqual(clean_options(options), options)


class CleanOptionsTest(unittest.TestCase):
    def test_fills_in_defaults_and_trims_title(self):
        self.assertEqual(clean_options({}), PRINTOUT_DEFAULTS)
        self.assertEqual(clean_options({"style": "grid", "title": "  Our house "}),
                         {**PRINTOUT_DEFAULTS, "style": "grid", "title": "Our house"})

    def test_rejects_unknown_names_and_bad_values(self):
        for changes in ({"style": "grid2"}, {"write_in_lines": 5}, {"write_in_lines": -1}, {"write_in_lines": True},
                        {"write_in_lines": "2"}, {"extra": 1}, {"colour": "theme"}, {"title": "x" * 41}, []):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                clean_options(changes)


class SvgTest(unittest.TestCase):
    def test_a_target_for_each_chore_box_with_its_check_state(self):
        # 4 Laundry dates and Windows for Bruno, one chore for Bella; write-in boxes get no target.
        sections = [section("Bruno", rows=[row("Laundry", dates=4, done=True), row("Windows")]), section("Bella", 1)]
        page = rendered(sections).svg_pages()[0]
        self.assertEqual(page.count('class="target"'), 6)
        self.assertEqual(page.count('data-done="true"'), 4)
        self.assertEqual(page.count('visibility="visible"'), 4)
        self.assertIn(">Laundry</text>", page)

    def test_an_svg_page_for_each_pdf_page(self):
        sheet = rendered(household(40), fit_page=False)
        self.assertEqual(len(sheet.svg_pages()), sheet.pages_count)

    def test_names_are_escaped(self):
        page = rendered([section("Bruno", rows=[row("Mop & <wax>")])]).svg_pages()[0]
        self.assertIn(">Mop &amp; &lt;wax&gt;</text>", page)
        self.assertNotIn("<wax>", page)


class CornerTest(unittest.TestCase):
    def test_corner_shapes_mirror_but_upright_ones_move(self):
        # A stem above the center: mirrored into the bottom-right corner it points down; upright it stays on top.
        def rounded(points):
            return [(round(x, 2), round(y, 2)) for x, y in points]

        stem_and_center = [(0.36, 0.25), (0.36, 0.37)]
        self.assertEqual(rounded(corner_points(stem_and_center, None, True, True, 8.5, 11)),
                         [(8.14, 10.75), (8.14, 10.63)])
        self.assertEqual(rounded(corner_points(stem_and_center, (0.36, 0.37), True, True, 8.5, 11)),
                         [(8.14, 10.51), (8.14, 10.63)])


if __name__ == "__main__":
    unittest.main()
