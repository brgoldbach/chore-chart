"""Due rules: which chores fall in a month, on which weeks, and for whom.

A chore's `align` month is any month in which it is due. Due dates repeat
in both directions from it, so months before `align` are due too. Owners
take turns per occurrence, counted from the aligned occurrence, so the
turns need no stored state. A shared chore goes to all its owners at once,
and its time splits evenly between them.

A week chore falls on its `weekday` (0 is Monday). With no weekday, each
occurrence stands for the week from Monday. Either way, an occurrence
belongs to the month that contains its date.
"""

from collections import Counter
from datetime import date, timedelta

UNIT_DAYS = {"week": 7, "month": 30, "year": 365}
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
NO_OWNER = ""


def parse_month(text):
    """Return the first day of a "YYYY-MM" month."""
    year, month = text.split("-")
    return date(int(year), int(month), 1)


def add_months(month, count):
    total = month.year * 12 + month.month - 1 + count
    return date(total // 12, total % 12 + 1, 1)


def months_between(start, month):
    return (month.year - start.year) * 12 + month.month - start.month


def first_weekday(month, weekday):
    return month + timedelta(days=(weekday - month.weekday()) % 7)


def weekdays_in(month, weekday):
    day = first_weekday(month, weekday)
    days = []
    while day.month == month.month:
        days.append(day)
        day += timedelta(weeks=1)
    return days


def in_season(chore, month_number):
    if not chore["season"]:
        return True
    start, end = chore["season"]
    if start <= end:
        return start <= month_number <= end
    return month_number >= start or month_number <= end


def interval_months(chore):
    return chore["every"] * (12 if chore["unit"] == "year" else 1)


def is_movable(chore):
    """Return True if shifting the aligned month changes which months are due."""
    return chore["unit"] != "week" and interval_months(chore) > 1


def occurrences(chore, month):
    """Return (key, day, index) for each occurrence of `chore` in `month`.

    `key` is the date for week-unit chores, else the month. `day` is that
    date's day of the month, or None. `index` counts intervals from the
    aligned occurrence (the first one in the aligned month) and is negative
    before it.
    """
    if not in_season(chore, month.month):
        return []
    align = parse_month(chore["align"])
    if chore["unit"] == "week":
        weekday = 0 if chore["weekday"] is None else chore["weekday"]
        anchor = first_weekday(align, weekday)
        found = []
        for day in weekdays_in(month, weekday):
            weeks = (day - anchor).days // 7
            if weeks % chore["every"] == 0:
                found.append((day.isoformat(), day.day, weeks // chore["every"]))
        return found
    interval = interval_months(chore)
    elapsed = months_between(align, month)
    if elapsed % interval:
        return []
    return [(f"{month:%Y-%m}", None, elapsed // interval)]


def owner_of(chore, index):
    owners = chore["owners"]
    return owners[index % len(owners)] if owners else NO_OWNER


def people_for(chore, index):
    """Return who does one occurrence: every sharer, the person whose turn it is, or nobody."""
    if chore["shared"]:
        return chore["owners"]
    owner = owner_of(chore, index)
    return [owner] if owner else []


def sort_key(chore):
    return chore["every"] * UNIT_DAYS[chore["unit"]], chore["name"].lower()


def interval_label(chore):
    unit = chore["unit"]
    label = unit if chore["every"] == 1 else f"{chore['every']} {unit}s"
    if unit == "week" and chore["weekday"] is not None:
        label += f" · {WEEKDAYS[chore['weekday']]}"
    return label


def duration(minutes):
    hours, minutes = divmod(round(minutes), 60)
    return " ".join(part for part in (f"{hours} h" if hours else "", f"{minutes} m" if minutes else "")
                    if part) or "0 m"


def short_names(owners):
    """Return {owner: shortest prefix that tells the owners apart}, e.g. Br, Be, A."""
    names = {}
    for owner in owners:
        length = 1
        while length < len(owner) and any(other != owner and other[:length].lower() == owner[:length].lower()
                                          for other in owners):
            length += 1
        names[owner] = owner[:length]
    return names


def chore_load(chore, months):
    """Return {(person, month index): minutes} for `chore` over `months`.

    Shared time splits evenly. NO_OWNER holds the time of unassigned chores.
    """
    load = Counter()
    if not chore["minutes"]:
        return load
    for position, month in enumerate(months):
        for _, _, index in occurrences(chore, month):
            people = people_for(chore, index) or [NO_OWNER]
            for person in people:
                load[(person, position)] += chore["minutes"] / len(people)
    return load


def total_load(chores, months):
    load = Counter()
    for chore in chores:
        load.update(chore_load(chore, months))
    return load


def due_sections(chores, owners, month, done=frozenset()):
    """Return the sheet for `month` as a list of sections.

    Every owner gets a section, then Shared (with 2 or more owners), then No
    owner (only with rows). A section is {"kind", "name", "title", "label",
    "minutes", "rows"}: `label` is `title` plus the load, and owner minutes
    include the person's part of shared chores. A
    chore with turns gives one row in each person's section, with only that
    person's boxes. A box is {"key", "day", "done"}, and `done` holds the
    checked (chore id, key) pairs.
    """
    sections = {("owner", owner): [] for owner in owners}
    if len(owners) > 1:
        sections[("shared", "")] = []
    sections[("none", "")] = []
    shared_minutes = 0
    for chore in sorted(chores, key=sort_key):
        boxes = {}
        for key, day, index in occurrences(chore, month):
            if chore["shared"]:
                section = ("shared", "")
                shared_minutes += chore["minutes"] or 0
            else:
                owner = owner_of(chore, index)
                section = ("owner", owner) if owner else ("none", "")
            boxes.setdefault(section, []).append({"key": key, "day": day, "done": (chore["id"], key) in done})
        for section, section_boxes in boxes.items():
            sections[section].append({"id": chore["id"], "name": chore["name"], "note": chore["note"],
                                      "every": interval_label(chore), "boxes": section_boxes})

    load = total_load(chores, [month])
    titles = {"owner": None, "shared": "Shared", "none": "No owner"}
    result = []
    for (kind, name), rows in sections.items():
        if kind == "none" and not rows:
            continue
        minutes = round(shared_minutes if kind == "shared" else load[(name, 0)])
        title = titles[kind] or name
        result.append({"kind": kind, "name": name, "rows": rows, "minutes": minutes, "title": title,
                       "label": f"{title} · {duration(minutes)}" if minutes else title})
    return result


def year_hours(chores, owners, months):
    """Return [(person, [minutes per month])] for each owner, then NO_OWNER if it has time."""
    load = total_load(chores, months)
    people = owners + ([NO_OWNER] if any(person == NO_OWNER for person, _ in load) else [])
    return [(person, [round(load[(person, position)]) for position in range(len(months))]) for person in people]


def calendar_rows(chores, owners, months):
    """Return one row per chore with who does it in each of `months`.

    A cell is "" when not due, "4×" for a week chore, "Sh" when shared,
    a short owner name, or "—" for no owner.
    """
    names = short_names(owners)
    rows = []
    for chore in sorted(chores, key=sort_key):
        cells = []
        for month in months:
            found = occurrences(chore, month)
            if not found:
                cells.append("")
            elif chore["unit"] == "week":
                cells.append(f"{len(found)}×")
            elif chore["shared"]:
                cells.append("Sh")
            else:
                cells.append(names.get(owner_of(chore, found[0][2]), "—"))
        rows.append({"id": chore["id"], "name": chore["name"], "people": chore["owners"],
                     "shared": chore["shared"], "movable": is_movable(chore), "cells": cells})
    return rows
