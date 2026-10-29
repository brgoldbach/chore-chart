"""Printable chore sheet: full-width owner sections, each with its chores in two columns.

Units are inches; font sizes are points.
"""

from math import ceil, floor

from fpdf import FPDF

from motifs import THEMES, theme_for

FONT_DIR = "/usr/share/fonts/dejavu"
MARGIN, TITLE_H, COLUMN_GAP = 0.5, 0.55, 0.3
SECTION_H, ROW_H, FONT_PT, MIN_FONT_PT = 0.4, 0.34, 12, 8
BLANK_ROWS = 4
BOX, BOX_PITCH, BOXES_W = 0.16, 0.25, 1.35
DAILY_COLUMNS, DAILY_ROW_H, DAILY_PT = 3, 0.24, 10


def render(month, sections, daily, paper):
    """Return the sheet for `month` with `sections` from schedule.due_sections.

    `daily` lists the daily chores, printed full width at the top without
    boxes. `paper` is "letter" or "a4". Each section lists its chores, then
    at least BLANK_ROWS blank rows, two to a line, left to right; one more
    blank completes a half-filled last line. Rows shrink to keep everything
    on one page, down to MIN_FONT_PT. Past that, a section continues on the
    next page. Full-width Extra rows fill the rest of the last page.
    """
    sheet = Sheet(month, paper)
    sheet.add_sections(sections, daily)
    return sheet


def lines_for(section):
    return ceil((len(section["rows"]) + BLANK_ROWS) / 2)


def corner_points(points, pivot, flip_x, flip_y, width, height):
    """Return a top-left corner shape's points in the corner that `flip_x` and `flip_y` select.

    A shape is mirrored into the corner. A shape with a `pivot` (see motifs.upright) moves to the
    mirrored spot without flipping instead, so faces and figures stay upright.
    """
    if pivot:
        u, v = pivot
        shift_x, shift_y = width - 2 * u if flip_x else 0, height - 2 * v if flip_y else 0
        return [(x + shift_x, y + shift_y) for x, y in points]
    return [(width - x if flip_x else x, height - y if flip_y else y) for x, y in points]


class Sheet(FPDF):
    def __init__(self, month, paper):
        super().__init__(unit="in", format=paper)
        self.set_margins(MARGIN, MARGIN)
        self.set_auto_page_break(False)
        self.add_font("DejaVu", "", f"{FONT_DIR}/DejaVuSans.ttf")
        self.add_font("DejaVu", "B", f"{FONT_DIR}/DejaVuSans-Bold.ttf")
        self.set_line_width(0.01)
        self.heading = f"Chores — {month:%B %Y}"
        self.set_title(self.heading)
        self.corners = THEMES[theme_for(month)]
        self.scale = 1
        self.daily = []
        self.column_w = (self.epw - COLUMN_GAP) / 2
        self.bottom = self.h - MARGIN

    def header(self):
        self.draw_corners()
        self.set_font("DejaVu", "B", 20)
        self.set_text_color(0)
        self.cell(0, TITLE_H, self.heading, new_x="LMARGIN", new_y="NEXT")
        if self.page_no() == 1 and self.daily:
            self.draw_daily()

    def draw_corners(self):
        """Draw the month's corner theme (see motifs.py), mirrored into all four corners."""
        self.set_line_width(0.012)
        for flip_x, flip_y in ((False, False), (True, False), (False, True), (True, True)):
            for kind, color, points, *pivot in self.corners:
                self.set_draw_color(*color)
                self.set_fill_color(*color)
                points = corner_points(points, pivot[0] if pivot else None, flip_x, flip_y, self.w, self.h)
                if kind == "line":
                    self.polyline(points)
                else:
                    self.polygon(points, style="F" if kind == "fill" else "D")
        self.set_line_width(0.01)

    def add_sections(self, sections, daily):
        needed = sum(SECTION_H + ROW_H * lines_for(section) for section in sections)
        if daily:
            needed += SECTION_H + DAILY_ROW_H * ceil(len(daily) / DAILY_COLUMNS)
        self.scale = max(min(1, (self.bottom - MARGIN - TITLE_H) / max(needed, ROW_H)), MIN_FONT_PT / FONT_PT)

        self.daily = daily
        self.add_page()
        if not sections:
            self.set_font("DejaVu", "", FONT_PT)
            self.cell(0, ROW_H, "No chores due this month.", new_x="LMARGIN", new_y="NEXT")
        for section in sections:
            self.draw_section(section)
        self.draw_extra()

    def column_x(self, column):
        return MARGIN + column * (self.column_w + COLUMN_GAP)

    def lines_left(self, y):
        # The tolerance stops float error from pushing an exact fit onto a new page.
        return floor((self.bottom - y) / (ROW_H * self.scale) + 1e-6)

    def draw_section(self, section):
        """Draw a heading, then the chores and blank rows two to a line, left to right.

        When the page runs out, the rest goes on a new page under "Title (cont.)".
        """
        scale = self.scale
        rows = section["rows"]
        slots = rows + [None] * (BLANK_ROWS + len(rows) % 2)
        label = section["label"]
        while slots:
            if self.lines_left(self.get_y() + SECTION_H * scale) < 1:
                self.add_page()
            top = self.get_y()
            self.draw_heading(label, MARGIN, top, self.epw)
            top += SECTION_H * scale
            lines = min(ceil(len(slots) / 2), self.lines_left(top))
            chunk, slots = slots[:2 * lines], slots[2 * lines:]
            for index, slot in enumerate(chunk):
                line, column = divmod(index, 2)
                x, y = self.column_x(column), top + line * ROW_H * scale
                if slot:
                    self.draw_row(slot, x, y)
                else:
                    self.draw_blank_row(x, y, self.column_w, who=False)
            self.set_y(top + lines * ROW_H * scale)
            label = f"{section['title']} (cont.)"

    def draw_extra(self):
        """Fill the rest of the last page with full-width write-in rows."""
        scale, top = self.scale, self.get_y()
        if self.lines_left(top + SECTION_H * scale) < 1:
            return
        self.draw_heading("Extra", MARGIN, top, self.epw)
        top += SECTION_H * scale
        for line in range(self.lines_left(top)):
            self.draw_blank_row(MARGIN, top + line * ROW_H * scale, self.epw, who=True)

    def draw_daily(self):
        # Daily chores have no boxes or owners: a plain list in columns, above the chore sections.
        scale, top = self.scale, self.get_y()
        self.draw_heading("Daily", MARGIN, top, self.epw)
        top += SECTION_H * scale
        width = self.epw / DAILY_COLUMNS
        self.set_font("DejaVu", "", DAILY_PT * scale)
        self.set_text_color(0)
        for index, name in enumerate(self.daily):
            row, column = divmod(index, DAILY_COLUMNS)
            self.text_cell(MARGIN + column * width, top + row * DAILY_ROW_H * scale, width,
                           DAILY_ROW_H * scale, f"• {name}")
        self.set_y(top + ceil(len(self.daily) / DAILY_COLUMNS) * DAILY_ROW_H * scale)

    def draw_heading(self, label, x, y, width):
        scale = self.scale
        self.set_fill_color(235)
        self.rect(x, y + 0.06 * scale, width, 0.3 * scale, style="F")
        self.set_font("DejaVu", "B", 12 * scale)
        self.set_text_color(0)
        self.text_cell(x, y + 0.06 * scale, width, 0.3 * scale, label)

    def draw_row(self, row, x, y):
        # Text centres on the boxes; the lower band of the row holds week labels and the note.
        scale = self.scale
        box, box_y = BOX * scale, y + 0.05 * scale
        for index, item in enumerate(row["boxes"]):
            box_x = x + 0.05 + index * BOX_PITCH
            self.set_draw_color(0)
            self.rect(box_x, box_y, box, box)
            if item["done"]:
                self.set_font("DejaVu", "B", 11 * scale)
                self.set_text_color(0)
                self.set_xy(box_x, box_y)
                self.cell(box, box, "✓", align="C")
            if item["day"]:
                self.set_font("DejaVu", "", 6 * scale)
                self.set_text_color(110)
                self.set_xy(box_x - 0.05, box_y + box)
                self.cell(box + 0.1, 0.09 * scale, str(item["day"]), align="C")

        name_x, name_w = x + BOXES_W, self.column_w - BOXES_W
        self.set_font("DejaVu", "", FONT_PT * scale)
        self.set_text_color(0)
        self.text_cell(name_x, y, name_w, 0.26 * scale, row["name"])
        if row["note"]:
            self.set_font("DejaVu", "", 7 * scale)
            self.set_text_color(110)
            self.text_cell(name_x, y + 0.22 * scale, name_w, 0.1 * scale, row["note"])

        bottom = y + ROW_H * scale
        self.set_draw_color(200)
        self.line(x, bottom, x + self.column_w, bottom)

    def draw_blank_row(self, x, y, width, who):
        # A write-in line for the chore; under Extra, a second line for who does it.
        scale = self.scale
        bottom, name_x, end = y + ROW_H * scale, x + BOXES_W, x + width
        self.set_draw_color(0)
        self.rect(x + 0.05, y + 0.05 * scale, BOX * scale, BOX * scale)
        self.set_draw_color(150)
        if who:
            self.line(name_x, bottom, end - 1.7, bottom)
            self.line(end - 1.5, bottom, end, bottom)
        else:
            self.line(name_x, bottom, end, bottom)

    def text_cell(self, x, y, width, height, text):
        self.set_xy(x, y)
        self.cell(width, height, self.fit(text, width - 2 * self.c_margin))

    def fit(self, text, width):
        if self.get_string_width(text) <= width:
            return text
        while text and self.get_string_width(text + "…") > width:
            text = text[:-1]
        return text + "…"
