"""Printable chore sheet in two styles: Cards (a card per person) and Week grid (a column per week).

The same drawing also comes out as SVG pages, so the Sheet tab shows the printed page (Sheet.svg_pages).
Units are inches; font sizes are points.
Related Documentation: DOCS.md ("The sheet").
"""

from calendar import monthrange
from html import escape
from math import ceil

from fpdf import FPDF

from motifs import ACCENTS, THEMES, theme_for
from schedule import duration

FONT_DIR = "/usr/share/fonts/dejavu"
MARGIN = 0.5
INK, MUTED, GRAY = (35, 35, 35), (120, 120, 120), (70, 70, 70)
RULE, FAINT, ZEBRA = (210, 210, 210), (228, 228, 228), (245, 245, 245)
# The colors a person can have: dark enough for heading text, distinct when printed.
PERSON_COLORS = {"teal": (36, 118, 140), "plum": (150, 70, 130), "green": (70, 120, 60), "orange": (190, 90, 30),
                 "blue": (60, 90, 160), "red": (160, 50, 60), "olive": (120, 100, 40), "slate": (90, 90, 110),
                 "purple": (110, 70, 170), "brown": (130, 85, 50)}

# Sizes at scale 1. The scale grows to the text-size limit when the page has room and shrinks to MIN_SCALE.
# Every row has the same height, with room for a note under the name or day numbers under the boxes,
# so the rows of cards side by side line up.
ROW_H, FONT_PT, BOX, BOX_PITCH, LABEL_GAP, LABEL_H = 0.33, 11, 0.15, 0.26, 0.035, 0.07
DAILY_ROW, DAILY_PAD, DAILY_GAP = 0.23, 0.14, 0.18
MIN_SCALE, EXTRA_LINES, TITLE_MAX = 8 / 11, 4, 40
# "Fit to one page" may shrink the text further, to 6.5 pt.
TIGHT_SCALE = 6.5 / 11
TEXT_SIZES = {"small": 0.9, "normal": 1.15, "large": 1.35}
# The font for the whole sheet: regular, bold, and italic files of each DejaVu family the image installs.
FONTS = {"sans": ("DejaVuSans", "DejaVuSans-Bold", "DejaVuSans-Oblique"),
         "serif": ("DejaVuSerif", "DejaVuSerif-Bold", "DejaVuSerif-Italic"),
         "condensed": ("DejaVuSansCondensed", "DejaVuSansCondensed-Bold", "DejaVuSansCondensed-Oblique")}
# The same families by name, for the SVG pages that a browser draws (the app serves the font files).
SVG_FAMILIES = {"sans": "DejaVu Sans", "serif": "DejaVu Serif", "condensed": "DejaVu Sans Condensed"}

# Each option's default and allowed values; None allows any value of the default's type.
PRINTOUT_OPTIONS = {
    "style": ("cards", ("cards", "grid")),
    "write_in_lines": (2, range(5)),
    "fit_page": (True, None),
    "orientation": ("portrait", ("portrait", "landscape")),
    "cards_per_row": (2, (1, 2, 3)),
    "text_size": ("normal", tuple(TEXT_SIZES)),
    "font": ("sans", tuple(FONTS)),
    "box_style": ("rounded", ("rounded", "square", "circle")),
    "frames": (True, None),
    "shading": (False, None),
    "color": ("theme", ("theme", "person", "gray")),
    "decoration": ("auto", ("auto", "none", *THEMES)),
    "title": ("", None),
    "daily": ("top", ("top", "bottom", "hidden")),
    "show_times": (True, None),
    "show_empty": (True, None),
    "extra": (True, None),
    "extra_who": (True, None),
}
PRINTOUT_DEFAULTS = {name: default for name, (default, _) in PRINTOUT_OPTIONS.items()}


def clean_options(options):
    """Return `options` with every printout option filled in from the defaults.

    Raise ValueError for an unknown name or a bad value. A value must have the
    type of its default, so True never passes as the number 1.
    """
    if not isinstance(options, dict) or not set(options) <= PRINTOUT_OPTIONS.keys():
        raise ValueError("Unknown printout option.")
    clean = {**PRINTOUT_DEFAULTS, **options}
    for name, value in clean.items():
        default, allowed = PRINTOUT_OPTIONS[name]
        if type(value) is not type(default) or (allowed is not None and value not in allowed):
            raise ValueError(f"Invalid printout option: {name}.")
    clean["title"] = clean["title"].strip()
    if len(clean["title"]) > TITLE_MAX:
        raise ValueError(f"The title can have at most {TITLE_MAX} characters.")
    return clean


PRESETS = {name: clean_options(changes) for name, changes in (
    ("Cards", {}),
    ("Week grid", {"style": "grid", "shading": True}),
    ("Basic", {"frames": False, "color": "gray", "decoration": "none", "box_style": "square", "write_in_lines": 1,
               "show_times": False, "extra_who": False}),
    ("Ink saver", {"color": "gray", "decoration": "none"}),
    ("Wide week grid", {"style": "grid", "orientation": "landscape", "color": "person", "shading": True}),
)}


def render(month, sections, daily, paper, options, colors):
    """Return the sheet for `month` with `sections` from schedule.due_sections.

    `daily` lists the daily chores, `paper` is "letter" or "a4", `options`
    comes from clean_options, and `colors` maps owner names to PERSON_COLORS
    names for the "person" color option. With room to spare, the text grows
    up to the text-size limit and leaves at least EXTRA_LINES Extra rows. A
    full month shrinks down to MIN_SCALE to stay on one page; past that, a
    section continues on the next page under "Title (cont.)".

    With "fit_page" on, a month that would run onto page 2 first gives up
    write-in lines, then the sections of people with no chores, then text
    size down to TIGHT_SCALE. The returned sheet's `fitted` lists what it
    gave up; the saved options do not change.
    """
    layout = GridSheet if options["style"] == "grid" else CardSheet

    def draw(changes, min_scale):
        changed = {**options, **changes}
        sheet = layout(month, printed_sections(sections, changed, colors), daily, paper, changed, min_scale)
        sheet.draw()
        return sheet

    sheet, fitted = draw({}, MIN_SCALE), []
    for changes, min_scale in fit_steps(options) if options["fit_page"] else ():
        if sheet.pages_count == 1:
            break
        sheet.output()  # releases the font files of the sheet that did not fit
        sheet = draw(changes, min_scale)
        lines, fitted = changes["write_in_lines"], []
        if lines != options["write_in_lines"]:
            fitted.append(f"{lines} write-in line{'' if lines == 1 else 's'}")
        if options["show_empty"] and not changes.get("show_empty", True):
            fitted.append("people with no chores hidden")
        if min_scale < MIN_SCALE:
            fitted.append("smaller text")
    sheet.fitted = fitted
    return sheet


def fit_steps(options):
    """Yield (option changes, smallest scale) for each try to fit one page, each giving up more than the last."""
    for lines in range(options["write_in_lines"] - 1, -1, -1):
        yield {"write_in_lines": lines}, MIN_SCALE
    yield {"write_in_lines": 0, "show_empty": False}, MIN_SCALE
    yield {"write_in_lines": 0, "show_empty": False}, TIGHT_SCALE


def printed_sections(sections, options, colors):
    """Return the sections to print, each with `color`: its owner's RGB color, or None.

    An owner without a color in `colors` gets the next of PERSON_COLORS that no
    one chose. Every owner gets a color before empty sections are hidden, so
    hiding them never changes a color. With times off, `minutes` is 0.
    """
    free = [name for name in PERSON_COLORS if name not in colors.values()] or list(PERSON_COLORS)
    printed, automatic = [], 0
    for section in sections:
        color = None
        if section["kind"] == "owner":
            color = colors.get(section["name"])
            if not color:
                color, automatic = free[automatic % len(free)], automatic + 1
        if section["rows"] or options["show_empty"]:
            # Each box carries its chore's id, so the screen copy of the page can check it off.
            rows = [{**row, "boxes": [{**item, "id": row["id"]} for item in row["boxes"]]} for row in section["rows"]]
            printed.append({**section, "rows": rows, "color": PERSON_COLORS[color] if color else None,
                            "minutes": section["minutes"] if options["show_times"] else 0})
    return printed


def week_spans(month):
    """Return the Week grid's columns for `month`: (first day, last day) of each 7 days from the 1st."""
    days = monthrange(month.year, month.month)[1]
    return [(start, min(start + 6, days)) for start in range(1, days + 1, 7)]


def hex_color(rgb):
    return "#%02x%02x%02x" % tuple(rgb)


def svg_color(color):
    return hex_color(round(value * 255) for value in color.colors)


def tint(color):
    return tuple(round(255 - (255 - value) * 0.12) for value in color)


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
    """The parts both styles share: page, title, daily list, boxes, and names.

    A subclass sets the body: draw_body and draw_extra draw it, and body_h,
    extra_h, and page_start_h measure it at the current scale.
    """

    def __init__(self, month, sections, daily, paper, options, min_scale=MIN_SCALE):
        super().__init__(orientation="L" if options["orientation"] == "landscape" else "P", unit="in",
                         format=paper)
        self.min_scale = min_scale
        self.set_margins(MARGIN, MARGIN)
        self.set_auto_page_break(False)
        for style, file in zip(("", "B", "I"), FONTS[options["font"]]):
            self.add_font("Body", style, f"{FONT_DIR}/{file}.ttf")
        self.month, self.sections, self.options = month, sections, options
        # Each page's drawing as SVG elements, and a target over each chore's box: see svg_pages.
        self.drawn, self.targets = [], []
        # Shaded rows mark themselves, so the line under each row is drawn only without shading.
        self.lined = not options["shading"]
        self.daily = [] if options["daily"] == "hidden" else daily
        self.heading = f"Chores — {month:%B %Y}"
        self.set_title(self.heading)
        decoration = options["decoration"]
        theme = theme_for(month) if decoration in ("auto", "none") else decoration
        self.corners = [] if decoration == "none" else THEMES[theme]
        self.accent = GRAY if options["color"] == "gray" else ACCENTS[theme]
        self.title_top = MARGIN - 0.02 + (0.2 if options["title"] else 0)
        self.body_top = self.title_top + 0.69
        self.bottom = self.h - MARGIN
        self.set_scale(1)

    def svg_pages(self):
        """Return each page as an SVG document: the same drawing as the PDF, in inches.

        Each chore's box gets a group with class "target" and data-id, data-key, and data-done:
        a transparent rect as wide as the box pitch, and the check mark, shown only when done.
        The screen flips the check at once on a tap, without drawing the page again.
        """
        family = SVG_FAMILIES[self.options["font"]]
        pages = []
        for page, elements in enumerate(self.drawn):
            targets = "".join(self.svg_target(*target) for on_page, *target in self.targets if on_page == page)
            pages.append(f'<svg xmlns="http://www.w3.org/2000/svg" class="page" '
                         f'viewBox="0 0 {self.w:.4f} {self.h:.4f}" font-family="{family}" style="font-kerning: none">'
                         f'<rect width="{self.w:.4f}" height="{self.h:.4f}" fill="#fff"/>{"".join(elements)}{targets}'
                         f'</svg>')
        return pages

    def svg_target(self, x, y, size, check, width, chore, key, done):
        points = " ".join(f"{px:.4f},{py:.4f}" for px, py in check)
        return (f'<g class="target" data-id="{escape(chore)}" data-key="{escape(key)}" data-done="{str(done).lower()}">'
                f'<rect x="{x:.4f}" y="{y:.4f}" width="{size:.4f}" height="{size:.4f}" fill="transparent"/>'
                f'<polyline class="check" points="{points}" fill="none" stroke="{hex_color(INK)}" '
                f'stroke-width="{width:.4f}" visibility="{"visible" if done else "hidden"}"/></g>')

    # Each drawing call below also goes into self.drawn as SVG. fpdf's polygon draws through polyline,
    # and its circle through ellipse, so those two are not overridden.
    def add_page(self, *args, **kwargs):
        self.drawn.append([])
        super().add_page(*args, **kwargs)

    def rect(self, x, y, w, h, style=None, round_corners=False, corner_radius=0):
        super().rect(x, y, w, h, style=style, round_corners=round_corners, corner_radius=corner_radius)
        corner = f' rx="{corner_radius:.4f}"' if round_corners else ""
        self.record(f'<rect x="{x:.4f}" y="{y:.4f}" width="{w:.4f}" height="{h:.4f}"{corner}', style)

    def line(self, x1, y1, x2, y2):
        super().line(x1, y1, x2, y2)
        self.record(f'<line x1="{x1:.4f}" y1="{y1:.4f}" x2="{x2:.4f}" y2="{y2:.4f}"', "D")

    def polyline(self, point_list, fill=False, polygon=False, style=None):
        super().polyline(point_list, fill=fill, polygon=polygon, style=style)
        points = " ".join(f"{x:.4f},{y:.4f}" for x, y in point_list)
        self.record(f'<{"polygon" if polygon else "polyline"} points="{points}"', style or ("F" if fill else "D"))

    def ellipse(self, x, y, w, h, style=None):
        super().ellipse(x, y, w, h, style=style)
        self.record(f'<ellipse cx="{x + w / 2:.4f}" cy="{y + h / 2:.4f}" rx="{w / 2:.4f}" ry="{h / 2:.4f}"', style)

    def cell(self, w=None, h=None, text="", *args, **kwargs):
        # fpdf sets the baseline 0.3 font sizes below the middle of the cell, after the cell margin.
        x, y = self.x, self.y
        result = super().cell(w, h, text, *args, **kwargs)
        if text:
            align = getattr(kwargs.get("align", "L"), "value", kwargs.get("align", "L"))
            anchor, text_x = {"C": ("middle", x + w / 2), "R": ("end", x + w - self.c_margin)}.get(
                align, ("start", x + self.c_margin))
            weight = ' font-weight="bold"' if "B" in self.font_style else ""
            slant = ' font-style="italic"' if "I" in self.font_style else ""
            baseline = y + 0.5 * h + 0.3 * self.font_size
            self.drawn[-1].append(
                f'<text x="{text_x:.4f}" y="{baseline:.4f}" text-anchor="{anchor}" font-size="{self.font_size:.4f}"'
                f'{weight}{slant} fill="{svg_color(self.text_color)}">{escape(text)}</text>')
        return result

    def record(self, element, style):
        style = str(getattr(style, "value", style) or "D")
        fill = svg_color(self.fill_color) if "F" in style else "none"
        stroke = f' stroke="{svg_color(self.draw_color)}" stroke-width="{self.line_width:.4f}"' if "D" in style else ""
        self.drawn[-1].append(f'{element} fill="{fill}"{stroke}/>')

    def set_scale(self, scale):
        self.scale = scale
        self.rh, self.box, self.pitch = ROW_H * scale, BOX * scale, BOX_PITCH * scale

    def draw(self):
        self.choose_scale()
        self.add_page()
        if not self.sections:
            self.set_font("Body", "", FONT_PT * self.scale)
            self.set_text_color(*INK)
            self.text_cell(MARGIN, self.get_y(), self.epw, self.rh, "No chores due this month.")
            self.set_y(self.get_y() + self.rh)
        self.draw_body()
        self.draw_tail()

    def choose_scale(self):
        # The largest scale up to the text-size limit that fits one page: growing past 1 must leave the
        # Extra rows, shrinking need not. Below min_scale the sheet runs onto more pages instead.
        def fits(scale, spare):
            self.set_scale(scale)
            extra = self.extra_h(EXTRA_LINES) if spare and self.options["extra"] else 0
            return self.daily_h() + self.page_start_h() + self.body_h() + extra <= self.bottom - self.body_top + 1e-6

        def largest(low, high, spare):
            if fits(high, spare):
                return high
            if not fits(low, spare):
                return None
            for _ in range(10):
                middle = (low + high) / 2
                low, high = (middle, high) if fits(middle, spare) else (low, middle)
            return low

        limit = TEXT_SIZES[self.options["text_size"]]
        self.set_scale((limit > 1 and largest(1, limit, True)) or largest(self.min_scale, min(1, limit), False)
                       or self.min_scale)

    def page_room(self):
        return self.bottom - self.body_top - self.page_start_h()

    def move_to_new_page(self, height):
        # A block that fits on a fresh page moves there, unless that leaves a third of this page empty.
        left = self.bottom - self.get_y()
        return left < height <= self.page_room() and left < self.page_room() / 3

    def page_start_h(self):
        return 0

    def page_start(self):
        """Draw what starts each page's body, below the title."""

    def header(self):
        self.draw_corners()
        if self.options["title"]:
            self.set_font("Body", "B", 9)
            self.set_text_color(*self.accent)
            self.set_char_spacing(0.015)
            self.set_xy(MARGIN, self.title_top - 0.2)
            self.cell(self.epw, 0.2, self.options["title"].upper())
            self.set_char_spacing(0)
        self.set_xy(MARGIN, self.title_top)
        self.set_font("Body", "B", 26)
        self.set_text_color(*self.accent)
        name = f"{self.month:%B}"
        self.cell(self.get_string_width(name) + 2 * self.c_margin, 0.5, name)
        self.set_font("Body", "", 26)
        self.set_text_color(*MUTED)
        self.cell(1.2, 0.5, f"{self.month:%Y}")
        self.set_draw_color(*self.accent)
        self.set_line_width(0.02)
        self.line(MARGIN, self.title_top + 0.57, MARGIN + self.epw, self.title_top + 0.57)
        self.set_line_width(0.012)
        self.set_y(self.body_top)
        if self.page_no() == 1 and self.daily and self.options["daily"] == "top":
            self.set_y(self.draw_daily(self.body_top) + DAILY_GAP * self.scale)
        self.page_start()

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
        self.set_line_width(0.012)

    def strip_h(self):
        return (ceil(len(self.daily) / 3) * DAILY_ROW + DAILY_PAD) * self.scale

    def daily_h(self):
        return self.strip_h() + DAILY_GAP * self.scale if self.daily else 0

    def draw_daily(self, top):
        """Draw the daily chores in a strip from `top`, three to a line. Return its bottom."""
        scale, height = self.scale, self.strip_h()
        label_w = 1.05 * scale
        if self.options["frames"]:
            self.set_fill_color(*tint(self.accent))
            self.rect(MARGIN, top, self.epw, height, style="F", round_corners=True, corner_radius=0.08)
        else:
            self.row_rule(MARGIN, top + height, self.epw)
        self.set_font("Body", "B", 8 * scale)
        self.set_text_color(*self.accent)
        self.set_xy(MARGIN + 0.05, top)
        self.cell(label_w - 0.05, height, "EVERY DAY")
        width = (self.epw - label_w) / 3
        self.set_font("Body", "", 10 * scale)
        self.set_text_color(*INK)
        for index, name in enumerate(self.daily):
            line, column = divmod(index, 3)
            self.text_cell(MARGIN + label_w + column * width, top + (DAILY_PAD / 2 + line * DAILY_ROW) * scale,
                           width, DAILY_ROW * scale, f"·  {name}")
        return top + height

    def draw_tail(self):
        # Extra fills the rest of the page, down to the daily list when that goes at the bottom.
        strip = self.strip_h() if self.daily and self.options["daily"] == "bottom" else 0
        limit = self.bottom - (strip + DAILY_GAP * self.scale if strip else 0)
        if self.get_y() > limit:
            self.add_page()
        if self.options["extra"]:
            self.draw_extra(limit)
        if strip:
            self.draw_daily(self.bottom - strip)

    def color_of(self, section):
        if self.options["color"] == "person" and section and section["color"]:
            return section["color"]
        return self.accent

    def draw_label(self, title, minutes, x, y, height, size, color):
        self.set_font("Body", "B", size * self.scale)
        self.set_text_color(*color)
        self.set_xy(x, y)
        self.cell(self.get_string_width(title) + 2 * self.c_margin, height, title)
        if minutes:
            self.set_font("Body", "", 8.5 * self.scale)
            self.set_text_color(*MUTED)
            self.cell(1.2, height, duration(minutes))

    def draw_box(self, x, y, item=None, label="below"):
        """Draw a check box at (x, y). A done item gets a ✓; a dated one gets its day `label` below or right."""
        size, scale = self.box, self.scale
        self.set_draw_color(*INK)
        self.set_line_width(0.012)
        if self.options["box_style"] == "circle":
            self.circle(x + size / 2, y + size / 2, size / 2)
        else:
            self.rect(x, y, size, size, round_corners=self.options["box_style"] == "rounded",
                      corner_radius=0.03 * scale)
        # Drawn, not typed: DejaVu Serif Bold has no ✓ glyph.
        check = [(x + 0.22 * size, y + 0.52 * size), (x + 0.42 * size, y + 0.74 * size),
                 (x + 0.8 * size, y + 0.26 * size)]
        if item and "id" in item:
            pad = (self.pitch - size) / 2
            self.targets.append((len(self.drawn) - 1, x - pad, y - pad, self.pitch, check, 0.018 * scale,
                                 item["id"], item["key"], item["done"]))
        if item and item["done"]:
            # The PDF only: the SVG page draws every target's check itself, so a tap can show or hide it.
            self.set_line_width(0.018 * scale)
            FPDF.polyline(self, check)
            self.set_line_width(0.012)
        if item and item["day"]:
            self.set_font("Body", "", (6.5 if label == "below" else 7.5) * scale)
            self.set_text_color(*MUTED)
            if label == "below":
                self.set_xy(x - 0.05, y + size + LABEL_GAP * scale)
                self.cell(size + 0.1, LABEL_H * scale, str(item["day"]), align="C")
            else:
                self.set_xy(x + size, y)
                self.cell(0.3 * scale, size, str(item["day"]))

    def name_middle(self, row, y):
        # A name centres in its row; with a note, the name and note centre together.
        return y + (0.115 * self.scale if row["note"] else self.rh / 2)

    def draw_name(self, row, x, middle, width):
        """Draw the chore name centred on `middle`, with its note below in small italics."""
        scale = self.scale
        self.set_font("Body", "", FONT_PT * scale)
        self.set_text_color(*INK)
        self.text_cell(x, middle - 0.1 * scale, width, 0.2 * scale, row["name"])
        if row["note"]:
            self.set_font("Body", "I", 7 * scale)
            self.set_text_color(*MUTED)
            self.text_cell(x, middle + 0.0875 * scale, width, 0.11 * scale, row["note"])

    def draw_band(self, x, y, width, height, color):
        """Draw a heading's background: a tinted band, or with frames off a rule in `color` under it."""
        if self.options["frames"]:
            self.set_fill_color(*tint(color))
            self.rect(x, y, width, height, style="F", round_corners=True, corner_radius=0.05)
            return
        self.set_draw_color(*color)
        self.set_line_width(0.015)
        self.line(x, y + height, x + width, y + height)
        self.set_line_width(0.012)

    def row_rule(self, x, y, width, who=False):
        """Draw the line under a row: the same for a chore and a write-in. `who` leaves a gap before a "who" part."""
        self.set_draw_color(*RULE)
        if who:
            self.line(x, y, x + width - 1.5, y)
            self.line(x + width - 1.35, y, x + width, y)
        else:
            self.line(x, y, x + width, y)

    def shade(self, x, y, width, height, index):
        if self.options["shading"] and index % 2:
            self.set_fill_color(*ZEBRA)
            self.rect(x, y, width, height, style="F")

    def text_cell(self, x, y, width, height, text):
        self.set_xy(x, y)
        self.cell(width, height, self.fit(text, width - 2 * self.c_margin))

    def fit(self, text, width):
        if self.get_string_width(text) <= width:
            return text
        while text and self.get_string_width(text + "…") > width:
            text = text[:-1]
        return text + "…"


class CardSheet(Sheet):
    """Cards: a rounded card per section, in rows that end level, then a full-width Extra card."""

    CARD_GAP, HEAD, TOP_PAD, PAD, RADIUS, INSET, COLUMN_GAP, WIDE_CARD = 0.15, 0.3, 0.02, 0.04, 0.1, 0.06, 0.25, 5

    def card_rows(self):
        """Return the rows of cards. A last row that is not full shares the page width."""
        per_row, rows = self.options["cards_per_row"], []
        for start in range(0, len(self.sections), per_row):
            group = self.sections[start:start + per_row]
            width = (self.epw - self.CARD_GAP * (len(group) - 1)) / len(group)
            rows.append(self.level([self.new_card(section, MARGIN + index * (width + self.CARD_GAP), width)
                                    for index, section in enumerate(group)]))
        return rows

    def new_card(self, section, x, width):
        # A wide card puts its chores two to a line; a blank completes a half-filled last line.
        columns = 2 if width > self.WIDE_CARD else 1
        slots = section["rows"] + [None] * self.options["write_in_lines"]
        slots += [None] * (-len(slots) % columns)
        return {"section": section, "title": section["title"], "minutes": section["minutes"], "x": x,
                "width": width, "columns": columns, "who": False,
                "lines": [slots[start:start + columns] for start in range(0, len(slots), columns)]}

    def level(self, cards):
        # The shorter cards of a row get more write-in lines, so all of them end level.
        height = max(self.card_h(card) for card in cards)
        for card in cards:
            card["lines"] = card["lines"] + [[None] * card["columns"]] * int((height - self.card_h(card)) / self.rh
                                                                              + 1e-6)
            card["height"] = height
        return cards

    def frame_h(self):
        return self.HEAD * self.scale + self.TOP_PAD + self.PAD

    def card_h(self, card):
        return self.frame_h() + sum(self.line_h(card, line) for line in card["lines"])

    def slot_w(self, card):
        columns = card["columns"]
        return (card["width"] - 2 * self.INSET - self.COLUMN_GAP * (columns - 1)) / columns

    def line_h(self, card, line):
        return max(self.slot_h(slot, self.slot_w(card)) for slot in line)

    def slot_h(self, row, width):
        return self.rh if not row or self.boxes_fit(row, width) else 2 * self.rh

    def boxes_fit(self, row, width):
        # A narrow card with many dates puts the boxes on a line of their own, under the name.
        if len(row["boxes"]) == 1:
            return True
        self.set_font("Body", "", FONT_PT * self.scale)
        return self.get_string_width(row["name"]) + 2 * self.c_margin + len(row["boxes"]) * self.pitch + 0.05 <= width

    def body_h(self):
        return sum(cards[0]["height"] + self.CARD_GAP for cards in self.card_rows())

    def extra_h(self, lines):
        return self.frame_h() + lines * self.rh

    def draw_body(self):
        for cards in self.card_rows():
            self.place(cards)

    def place(self, cards):
        """Draw a row of cards at the cursor. A row too tall for a page continues on the next under "(cont.)"."""
        height = cards[0]["height"]
        if self.move_to_new_page(height):
            self.add_page()
        top = self.get_y()
        if top + height <= self.bottom + 1e-6:
            for card in cards:
                self.draw_card(card, top)
            self.set_y(top + height + self.CARD_GAP)
            return
        room = self.bottom - self.get_y() - self.frame_h()
        if room < max(self.line_h(card, card["lines"][0]) for card in cards if card["lines"]):
            self.add_page()
            room = self.bottom - self.get_y() - self.frame_h()
        now, later = [], []
        for card in cards:
            count, used = 0, 0
            while count < len(card["lines"]) and used + self.line_h(card, card["lines"][count]) <= room + 1e-6:
                used += self.line_h(card, card["lines"][count])
                count += 1
            now.append({**card, "lines": card["lines"][:count]})
            if any(slot for line in card["lines"][count:] for slot in line):
                later.append({**card, "title": f"{card['section']['title']} (cont.)", "minutes": 0,
                              "lines": card["lines"][count:]})
        top, now = self.get_y(), self.level(now)
        for card in now:
            self.draw_card(card, top)
        self.set_y(top + now[0]["height"] + self.CARD_GAP)
        if later:
            self.add_page()
            self.place(self.level(later))

    def draw_card(self, card, top):
        x, width, height, head = card["x"], card["width"], card["height"], self.HEAD * self.scale
        frames, color = self.options["frames"], self.color_of(card["section"])
        if frames:
            self.set_fill_color(*tint(color))
            self.rect(x, top, width, head, style="F", round_corners=True, corner_radius=self.RADIUS)
            self.rect(x, top + head / 2, width, head / 2, style="F")
            self.set_draw_color(*RULE)
            self.set_line_width(0.012)
            self.rect(x, top, width, height, style="D", round_corners=True, corner_radius=self.RADIUS)
        else:
            self.draw_band(x, top, width, head, color)
        self.draw_label(card["title"], card["minutes"], x + self.INSET, top, head, 12, color)

        # Every row, chore or write-in, ends in the same rule; in a framed card the border closes the last row.
        slot_w, rows_top = self.slot_w(card), top + head + self.TOP_PAD
        y = rows_top
        for index, line in enumerate(card["lines"]):
            line_h = self.line_h(card, line)
            self.shade(x + 0.03, y, width - 0.06, line_h, index)
            for column, slot in enumerate(line):
                slot_x = x + self.INSET + column * (slot_w + self.COLUMN_GAP)
                if slot:
                    self.draw_chore(slot, slot_x, y, slot_w)
                else:
                    self.draw_box(slot_x + slot_w - self.pitch + (self.pitch - self.box) / 2,
                                  self.box_y([], y))
                if self.lined and (not frames or index < len(card["lines"]) - 1):
                    self.row_rule(slot_x, y + line_h, slot_w, who=card["who"])
            y += line_h
        if card["who"] and not self.lined:
            # Without rules to split, a divider keeps the "who" part apart, where the rule's gap would be.
            divider = x + self.INSET + slot_w - 1.425
            self.set_draw_color(*FAINT)
            self.line(divider, rows_top, divider, y)

    def box_y(self, boxes, y):
        # Boxes centre in the row from `y`; boxes with day numbers centre together with the numbers.
        labels = (LABEL_GAP + LABEL_H) * self.scale if any(item["day"] for item in boxes) else 0
        return y + (self.rh - self.box - labels) / 2

    def draw_chore(self, row, x, y, width):
        # The boxes go on the right, or on a second row under the name when they do not fit there.
        boxes, middle = row["boxes"], self.name_middle(row, y)
        if not self.boxes_fit(row, width):
            self.draw_name(row, x, middle, width)
            for index, item in enumerate(boxes):
                self.draw_box(x + self.c_margin + index * self.pitch, self.box_y(boxes, y + self.rh), item)
            return
        boxes_w = len(boxes) * self.pitch
        for index, item in enumerate(boxes):
            self.draw_box(x + width - boxes_w + index * self.pitch + (self.pitch - self.box) / 2,
                          self.box_y(boxes, y), item)
        self.draw_name(row, x, middle, width - boxes_w - 0.05)

    def draw_extra(self, limit):
        lines = int((limit - self.get_y() - self.frame_h()) / self.rh + 1e-6)
        if lines < 1:
            return
        self.draw_card({"section": None, "title": "Extra", "minutes": 0, "x": MARGIN, "width": self.epw,
                        "columns": 1, "who": self.options["extra_who"], "lines": [[None]] * lines,
                        "height": self.extra_h(lines)}, self.get_y())


class GridSheet(Sheet):
    """Week grid: one table with a column per 7 days, so each dated box sits in its week."""

    COLUMN_HEAD, GROUP_HEAD, GROUP_GAP = 0.26, 0.32, 0.06

    def __init__(self, month, sections, daily, paper, options, min_scale=MIN_SCALE):
        super().__init__(month, sections, daily, paper, options, min_scale)
        self.weeks = week_spans(month)
        self.name_w, any_w = 0.37 * self.epw, 0.107 * self.epw
        week_w = (self.epw - self.name_w - any_w) / len(self.weeks)
        self.columns = [(MARGIN + self.name_w, any_w)] + [
            (MARGIN + self.name_w + any_w + index * week_w, week_w) for index in range(len(self.weeks))]

    def page_start_h(self):
        return (self.COLUMN_HEAD + self.GROUP_GAP) * self.scale

    def page_start(self):
        top, head = self.get_y(), self.COLUMN_HEAD * self.scale
        self.set_font("Body", "B", 7.5 * self.scale)
        self.set_text_color(*MUTED)
        self.set_xy(MARGIN, top)
        self.cell(self.name_w, head, "CHORE")
        labels = ["ANY TIME"] + [f"{start}–{end}" if start != end else str(start) for start, end in self.weeks]
        labels[1] = f"{self.month:%b} {labels[1]}".upper()
        for (x, width), label in zip(self.columns, labels):
            self.set_xy(x, top)
            self.cell(width, head, label, align="C")
        self.set_draw_color(*INK)
        self.line(MARGIN, top + head, MARGIN + self.epw, top + head)
        self.set_y(top + self.page_start_h())

    def slots(self, section):
        return section["rows"] + [None] * self.options["write_in_lines"]

    def body_h(self):
        return sum((self.GROUP_HEAD + self.GROUP_GAP) * self.scale + len(self.slots(section)) * self.rh
                   for section in self.sections)

    def extra_h(self, lines):
        return self.GROUP_HEAD * self.scale + lines * self.rh

    def draw_body(self):
        for section in self.sections:
            self.place(section, self.slots(section), section["title"], section["minutes"], 0)

    def place(self, section, slots, title, minutes, first):
        """Draw a group at the cursor. A group too tall for a page continues on the next under "(cont.)"."""
        head = self.GROUP_HEAD * self.scale
        if self.move_to_new_page(head + len(slots) * self.rh):
            self.add_page()
        count = min(len(slots), int((self.bottom - self.get_y() - head) / self.rh + 1e-6))
        if slots and count < 1:
            self.add_page()
            count = min(len(slots), int((self.bottom - self.get_y() - head) / self.rh + 1e-6))
        self.draw_group(section, slots[:count], title, minutes, first)
        if count < len(slots):
            self.add_page()
            self.place(section, slots[count:], f"{section['title']} (cont.)", 0, first + count)

    def draw_group(self, section, slots, title, minutes, first):
        # Rows alternate shading from the group's first row; `first` keeps the pattern on a continued group.
        top, head, color = self.get_y(), self.GROUP_HEAD * self.scale, self.color_of(section)
        self.draw_band(MARGIN, top, self.epw, head, color)
        self.draw_label(title, minutes, MARGIN + 0.03, top, head, 11, color)
        y = top + head
        for index, slot in enumerate(slots, first):
            self.shade(MARGIN, y, self.epw, self.rh, index)
            if slot:
                self.draw_row(slot, y)
            else:
                self.any_box(y)
            if self.lined:
                self.row_rule(MARGIN, y + self.rh, self.epw)
            y += self.rh
        self.set_draw_color(*FAINT)
        for x, _ in self.columns:
            self.line(x, top + head, x, y)
        self.set_y(y + self.GROUP_GAP * self.scale)

    def any_box(self, y, item=None):
        x, width = self.columns[0]
        self.draw_box(x + (width - self.box) / 2, y + (self.rh - self.box) / 2, item)

    def draw_row(self, row, y):
        self.draw_name(row, MARGIN, self.name_middle(row, y), self.name_w)
        for item in row["boxes"]:
            if not item["day"]:
                self.any_box(y, item)
                continue
            week = next(index for index, (start, end) in enumerate(self.weeks) if start <= item["day"] <= end)
            x, width = self.columns[week + 1]
            self.draw_box(x + width / 2 - self.box / 2 - 0.08 * self.scale, y + (self.rh - self.box) / 2, item,
                          label="right")

    def draw_extra(self, limit):
        top, head = self.get_y(), self.GROUP_HEAD * self.scale
        lines = int((limit - top - head) / self.rh + 1e-6)
        if lines < 1:
            return
        self.draw_band(MARGIN, top, self.epw, head, self.accent)
        self.draw_label("Extra", 0, MARGIN + 0.03, top, head, 11, self.accent)
        for line in range(lines):
            # The "who" part runs under the week columns; the gap under Any time holds the box.
            y = top + head + line * self.rh
            self.shade(MARGIN, y, self.epw, self.rh, line)
            self.any_box(y)
            if not self.lined:
                continue
            if self.options["extra_who"]:
                self.row_rule(MARGIN, y + self.rh, self.name_w)
                self.row_rule(self.columns[1][0], y + self.rh, MARGIN + self.epw - self.columns[1][0])
            else:
                self.row_rule(MARGIN, y + self.rh, self.epw)
        self.set_y(top + head + lines * self.rh)
