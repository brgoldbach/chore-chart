import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "app"))

from server import BadRequest, clean_names, rename_owner, validate_chores, validate_owners  # noqa: E402


def chore(*owners, **fields):
    return {"name": "Chore", "owners": list(owners), "every": 1, "unit": "month", "align": "2026-11", **fields}


class ValidateOwnersTest(unittest.TestCase):
    def test_strips_names(self):
        self.assertEqual(validate_owners([" Sam ", "Bruno"], []), ["Sam", "Bruno"])

    def test_rejects_blank_and_duplicate_names(self):
        for owners in (["Sam", ""], ["Sam", "sam"]):
            with self.assertRaises(BadRequest):
                validate_owners(owners, [])

    def test_blocks_removing_owner_with_chores(self):
        with self.assertRaisesRegex(BadRequest, "Sam"):
            validate_owners(["Bruno"], [chore("Bruno", "Sam")])

    def test_allows_removing_owner_without_chores(self):
        self.assertEqual(validate_owners(["Bruno"], [chore("Bruno"), chore()]), ["Bruno"])


class RenameOwnerTest(unittest.TestCase):
    def test_renames_in_owner_list_and_chores_keeping_order(self):
        chores = [chore("Sam", "Bella"), chore("Bella", "Sam", shared=True), chore("Alex")]
        owners, renamed = rename_owner(["Sam", "Bella", "Alex"], chores, "Bella", " Isabella ")
        self.assertEqual(owners, ["Sam", "Isabella", "Alex"])
        self.assertEqual([item["owners"] for item in renamed], [["Sam", "Isabella"], ["Isabella", "Sam"], ["Alex"]])
        self.assertTrue(renamed[1]["shared"])

    def test_rejects_clash_blank_and_unknown(self):
        for old, new in (("Bella", "sam"), ("Bella", " "), ("Zed", "Zoe")):
            with self.assertRaises(BadRequest):
                rename_owner(["Sam", "Bella"], [], old, new)


class DailyNamesTest(unittest.TestCase):
    def test_trims_and_rejects_repeats(self):
        self.assertEqual(clean_names([" Load dishwasher ", "Vacuum"], "daily chores"), ["Load dishwasher", "Vacuum"])
        with self.assertRaisesRegex(BadRequest, "Daily chores must be unique"):
            clean_names(["Vacuum", "vacuum"], "daily chores")
        with self.assertRaises(BadRequest):
            clean_names("Vacuum", "daily chores")


class ValidateChoresTest(unittest.TestCase):
    def test_accepts_turns_and_no_owner(self):
        self.assertEqual(len(validate_chores([chore("Sam", "Bruno"), chore()], ["Sam", "Bruno"])), 2)

    def test_rejects_unknown_or_repeated_owner(self):
        for owners in (("Alex",), ("Sam", "Sam")):
            with self.assertRaisesRegex(BadRequest, "owner"):
                validate_chores([chore(*owners)], ["Sam"])

    def test_assigns_id_once(self):
        first = validate_chores([chore()], [])[0]
        self.assertTrue(first["id"])
        self.assertEqual(validate_chores([first], [])[0]["id"], first["id"])

    def test_optional_fields_default(self):
        # A chore saved before a field existed must still load.
        item = validate_chores([chore()], [])[0]
        self.assertEqual((item["minutes"], item["season"], item["note"], item["shared"], item["weekday"]),
                         (None, None, "", False, None))

    def test_weekday_only_for_week_chores(self):
        self.assertEqual(validate_chores([chore(unit="week", weekday=1)], [])[0]["weekday"], 1)
        self.assertIsNone(validate_chores([chore(weekday=1)], [])[0]["weekday"])
        with self.assertRaises(BadRequest):
            validate_chores([chore(unit="week", weekday=7)], [])

    def test_shared_needs_two_owners(self):
        with self.assertRaisesRegex(BadRequest, "shared"):
            validate_chores([chore("Sam", shared=True)], ["Sam"])
        self.assertTrue(validate_chores([chore("Sam", "Bruno", shared=True)], ["Sam", "Bruno"])[0]["shared"])

    def test_rejects_bad_season_and_minutes(self):
        for fields in ({"season": [0, 5]}, {"season": [4]}, {"minutes": -5}):
            with self.assertRaises(BadRequest):
                validate_chores([chore(**fields)], [])


if __name__ == "__main__":
    unittest.main()
