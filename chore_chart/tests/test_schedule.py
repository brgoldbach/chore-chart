import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "app"))

from schedule import (add_months, calendar_rows, due_sections, duration, parse_month, short_names,  # noqa: E402
                      weekdays_in)

TUESDAY = 1


def chore(every, unit, align, name="Chore", owners=("Sam",), minutes=None, season=None, note="", shared=False,
          weekday=None):
    return {"id": name, "name": name, "owners": list(owners), "every": every, "unit": unit, "align": align,
            "minutes": minutes, "season": season, "note": note, "shared": shared, "weekday": weekday}


def sections(chores, month, owners=("Sam", "Bruno"), done=frozenset()):
    return due_sections(chores, list(owners), parse_month(month), done)


def rows_by_section(chores, month, owners=("Sam", "Bruno")):
    """Return {owner name, "shared", or "none": rows} for the sections that have rows."""
    return {section["name"] if section["kind"] == "owner" else section["kind"]: section["rows"]
            for section in sections(chores, month, owners) if section["rows"]}


def due_months(chore_, months):
    return [month for month in months if rows_by_section([chore_], month)]


def days_by_owner(chore_, month):
    return {name: [box["day"] for box in rows[0]["boxes"]] for name, rows in rows_by_section([chore_], month).items()}


def year_from(start):
    return [add_months(parse_month(start), offset) for offset in range(12)]


class MonthUnitTest(unittest.TestCase):
    def test_monthly_is_due_every_month(self):
        months = ["2026-01", "2026-10", "2026-11", "2027-03"]
        self.assertEqual(due_months(chore(1, "month", "2026-11"), months), months)

    def test_every_three_months_back_populates(self):
        months = [f"2026-{month:02}" for month in range(1, 13)] + ["2027-01", "2027-02"]
        self.assertEqual(due_months(chore(3, "month", "2026-11"), months),
                         ["2026-02", "2026-05", "2026-08", "2026-11", "2027-02"])

    def test_yearly_and_every_two_years(self):
        months = ["2024-04", "2025-04", "2026-04", "2027-04", "2027-05", "2028-04"]
        self.assertEqual(due_months(chore(1, "year", "2026-04"), months),
                         ["2024-04", "2025-04", "2026-04", "2027-04", "2028-04"])
        self.assertEqual(due_months(chore(2, "year", "2026-04"), months),
                         ["2024-04", "2026-04", "2028-04"])

    def test_month_row_has_one_box_keyed_by_month(self):
        row = rows_by_section([chore(1, "month", "2026-11")], "2026-11")["Sam"][0]
        self.assertEqual(row["boxes"], [{"key": "2026-11", "day": None, "done": False}])


class WeekUnitTest(unittest.TestCase):
    def test_mondays_in_month(self):
        self.assertEqual([day.day for day in weekdays_in(date(2026, 11, 1), 0)], [2, 9, 16, 23, 30])
        self.assertEqual([day.day for day in weekdays_in(date(2027, 2, 1), 0)], [1, 8, 15, 22])

    def test_weekly_box_per_monday(self):
        self.assertEqual(days_by_owner(chore(1, "week", "2026-11"), "2026-11"), {"Sam": [2, 9, 16, 23, 30]})

    def test_every_two_weeks_keeps_phase_across_months(self):
        fortnightly = chore(2, "week", "2026-11")
        self.assertEqual(days_by_owner(fortnightly, "2026-11"), {"Sam": [2, 16, 30]})
        self.assertEqual(days_by_owner(fortnightly, "2026-12"), {"Sam": [14, 28]})

    def test_every_two_weeks_back_populates(self):
        # Anchor is Monday 2026-12-07; two and four weeks earlier are due.
        self.assertEqual(days_by_owner(chore(2, "week", "2026-12"), "2026-11"), {"Sam": [9, 23]})

    def test_month_without_due_week_is_skipped(self):
        # Due Mondays: 2026-11-02, 2026-12-14, 2027-01-25, 2027-03-08.
        self.assertEqual(due_months(chore(6, "week", "2026-11"), ["2027-01", "2027-02"]), ["2027-01"])

    def test_week_box_key_is_monday(self):
        row = rows_by_section([chore(1, "week", "2026-11")], "2026-11")["Sam"][0]
        self.assertEqual(row["boxes"][0]["key"], "2026-11-02")


class WeekdayTest(unittest.TestCase):
    def test_tuesday_on_the_1st_goes_to_the_next_month(self):
        # Any day: the week of Monday Nov 30 is on November's sheet. Tuesday: that week's Dec 1 is on December's.
        laundry = chore(1, "week", "2026-11", weekday=TUESDAY)
        self.assertEqual(days_by_owner(chore(1, "week", "2026-11"), "2026-11"), {"Sam": [2, 9, 16, 23, 30]})
        self.assertEqual(days_by_owner(laundry, "2026-11"), {"Sam": [3, 10, 17, 24]})
        self.assertEqual(days_by_owner(laundry, "2026-12"), {"Sam": [1, 8, 15, 22, 29]})

    def test_every_two_weeks_on_tuesday(self):
        # Anchor is the first Tuesday of the aligned month: Nov 3.
        mopping = chore(2, "week", "2026-11", weekday=TUESDAY)
        self.assertEqual(days_by_owner(mopping, "2026-11"), {"Sam": [3, 17]})
        self.assertEqual(days_by_owner(mopping, "2026-12"), {"Sam": [1, 15, 29]})
        self.assertEqual(days_by_owner(mopping, "2026-10"), {"Sam": [6, 20]})

    def test_key_is_the_date(self):
        row = rows_by_section([chore(1, "week", "2026-11", weekday=TUESDAY)], "2026-11")["Sam"][0]
        self.assertEqual(row["boxes"][0]["key"], "2026-11-03")

    def test_label_names_the_day(self):
        chores = [chore(1, "week", "2026-11", "A", weekday=TUESDAY), chore(2, "week", "2026-11", "B", weekday=6)]
        rows = rows_by_section(chores, "2026-11")["Sam"]
        self.assertEqual([row["every"] for row in rows], ["week · Tue", "2 weeks · Sun"])


class TurnTest(unittest.TestCase):
    def test_weekly_turns_split_into_owner_sections(self):
        bathrooms = chore(1, "week", "2026-11", owners=("Sam", "Bruno"))
        self.assertEqual(days_by_owner(bathrooms, "2026-11"), {"Sam": [2, 16, 30], "Bruno": [9, 23]})

    def test_turns_back_populate(self):
        # October Mondays are 4, 3, 2, and 1 weeks before the anchor (Nov 2).
        bathrooms = chore(1, "week", "2026-11", owners=("Sam", "Bruno"))
        self.assertEqual(days_by_owner(bathrooms, "2026-10"), {"Sam": [5, 19], "Bruno": [12, 26]})

    def test_monthly_turns(self):
        cabinets = chore(3, "month", "2026-11", owners=("Sam", "Bruno"))
        owners = [list(rows_by_section([cabinets], month))[0] for month in ("2026-08", "2026-11", "2027-02")]
        self.assertEqual(owners, ["Bruno", "Sam", "Bruno"])


class SharedTest(unittest.TestCase):
    def test_shared_chore_lists_once_and_splits_time(self):
        bathrooms = chore(1, "month", "2026-11", owners=("Sam", "Bruno"), minutes=90, shared=True)
        result = {section["kind"] + section["name"]: section for section in sections([bathrooms], "2026-11")}
        self.assertEqual(len(result["shared"]["rows"]), 1)
        self.assertEqual(result["shared"]["label"], "Shared · 1 h 30 m")
        self.assertEqual((result["shared"]["title"], result["ownerSam"]["title"]), ("Shared", "Sam"))
        self.assertEqual((result["ownerSam"]["label"], result["ownerBruno"]["label"]), ("Sam · 45 m", "Bruno · 45 m"))
        self.assertEqual(result["ownerSam"]["rows"], [])

    def test_shared_by_three_splits_in_thirds(self):
        owners = ("Sam", "Bruno", "Alex")
        shared = chore(1, "month", "2026-11", owners=owners, minutes=90, shared=True)
        labels = [section["label"] for section in sections([shared], "2026-11", owners) if section["kind"] == "owner"]
        self.assertEqual(labels, ["Sam · 30 m", "Bruno · 30 m", "Alex · 30 m"])


class SectionTest(unittest.TestCase):
    def test_every_owner_and_shared_always_present(self):
        result = sections([], "2026-11")
        self.assertEqual([(section["kind"], section["name"]) for section in result],
                         [("owner", "Sam"), ("owner", "Bruno"), ("shared", "")])

    def test_no_shared_section_for_one_owner(self):
        self.assertEqual([section["kind"] for section in sections([], "2026-11", owners=("Sam",))], ["owner"])

    def test_no_owner_section_only_with_rows(self):
        result = sections([chore(1, "month", "2026-11", owners=())], "2026-11")
        self.assertEqual(result[-1]["kind"], "none")
        self.assertEqual(result[-1]["label"], "No owner")

    def test_rows_sort_by_interval_then_name(self):
        chores = [chore(1, "year", "2026-11", "Gutters"), chore(1, "month", "2026-11", "filter"),
                  chore(1, "week", "2026-11", "Trash"), chore(1, "week", "2026-11", "dishes")]
        rows = rows_by_section(chores, "2026-11")["Sam"]
        self.assertEqual([row["name"] for row in rows], ["dishes", "Trash", "filter", "Gutters"])

    def test_load_counts_each_box(self):
        chores = [chore(1, "week", "2026-11", "Trash", minutes=15), chore(1, "month", "2026-11", "Filter")]
        self.assertEqual(sections(chores, "2026-11")[0]["label"], "Sam · 1 h 15 m")

    def test_done_marks_box(self):
        result = sections([chore(1, "week", "2026-11", "Trash")], "2026-11", done={("Trash", "2026-11-09")})
        self.assertEqual([box["done"] for box in result[0]["rows"][0]["boxes"]],
                         [False, True, False, False, False])

    def test_interval_label(self):
        chores = [chore(1, "week", "2026-11", "A"), chore(6, "month", "2026-11", "B")]
        self.assertEqual([row["every"] for row in rows_by_section(chores, "2026-11")["Sam"]], ["week", "6 months"])

    def test_duration(self):
        self.assertEqual([duration(minutes) for minutes in (0, 45, 120, 190, 22.5)],
                         ["0 m", "45 m", "2 h", "3 h 10 m", "22 m"])


class SeasonTest(unittest.TestCase):
    def test_season_skips_months_outside(self):
        mowing = chore(1, "week", "2026-11", season=[4, 10])
        self.assertEqual(due_months(mowing, ["2026-03", "2026-04", "2026-10", "2026-11"]), ["2026-04", "2026-10"])

    def test_season_wraps_year_end(self):
        snow = chore(1, "month", "2026-11", season=[11, 3])
        self.assertEqual(due_months(snow, ["2026-10", "2026-11", "2027-01", "2027-03", "2027-04"]),
                         ["2026-11", "2027-01", "2027-03"])

    def test_turns_count_off_season_months(self):
        # April 2027 is index 11 from May 2026, so Bruno has it after Bruno's October.
        mowing = chore(1, "month", "2026-05", owners=("Sam", "Bruno"), season=[4, 10])
        owners = [list(rows_by_section([mowing], month))[0] for month in ("2026-05", "2026-10", "2027-04")]
        self.assertEqual(owners, ["Sam", "Bruno", "Bruno"])


class CalendarTest(unittest.TestCase):
    def test_short_names(self):
        self.assertEqual(short_names(["Bruno", "Bella", "Ada"]), {"Bruno": "Br", "Bella": "Be", "Ada": "A"})
        self.assertEqual(short_names(["Al", "Alex"]), {"Al": "Al", "Alex": "Ale"})

    def test_cells(self):
        owners = ["Bruno", "Bella"]
        chores = [chore(1, "month", "2026-11", "Turns", owners=owners),
                  chore(2, "month", "2026-11", "Shared", owners=owners, shared=True),
                  chore(1, "week", "2026-11", "Weekly", owners=["Bruno"]),
                  chore(6, "month", "2026-11", "Nobody", owners=())]
        rows = {row["name"]: row["cells"][:3] for row in calendar_rows(chores, owners, year_from("2026-11"))}
        self.assertEqual(rows["Turns"], ["Br", "Be", "Br"])
        self.assertEqual(rows["Shared"], ["Sh", "", "Sh"])
        self.assertEqual(rows["Weekly"], ["5×", "4×", "4×"])
        self.assertEqual(rows["Nobody"], ["—", "", ""])

    def test_movable(self):
        chores = [chore(1, "week", "2026-11", "W"), chore(1, "month", "2026-11", "M1"),
                  chore(3, "month", "2026-11", "M3"), chore(1, "year", "2026-11", "Y")]
        movable = {row["name"]: row["movable"] for row in calendar_rows(chores, ["Sam"], year_from("2026-11"))}
        self.assertEqual(movable, {"W": False, "M1": False, "M3": True, "Y": True})

    def test_weekday_changes_weekly_count(self):
        # November 2026 has 5 Mondays but 4 Tuesdays.
        chores = [chore(1, "week", "2026-11", "Mon"), chore(1, "week", "2026-11", "Tue", weekday=TUESDAY)]
        cells = {row["name"]: row["cells"][0] for row in calendar_rows(chores, ["Sam"], year_from("2026-11"))}
        self.assertEqual(cells, {"Mon": "5×", "Tue": "4×"})


if __name__ == "__main__":
    unittest.main()
