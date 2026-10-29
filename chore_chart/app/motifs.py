"""Corner decorations for the printed sheet: a theme per season, and holiday themes.

A theme is the top-left corner as shapes, in inches from the corner:
("line", color, points) is an open line, ("outline", color, points) a closed
outline, and ("fill", color, points) a filled shape. The sheet mirrors the
corner into the other three. Every point stays at least 0.2 in from the paper
edge, which inkjets can print, and inside the 0.5 in margin. Corner pieces sit
on the diagonal and mirror onto themselves, so all four corners point inward.

A shape can carry a fourth item, a pivot point (see upright()). The sheet
then moves it to the mirrored spot without flipping it, so faces and figures
stay upright in every corner.
"""

from datetime import date
from math import cos, pi, sin

CORNER = (0.34, 0.34)
INWARD = pi / 4
VINE_STEPS = 12


def cubic(p0, p1, p2, p3, steps=VINE_STEPS):
    """Return points along the cubic Bézier curve p0..p3."""
    return [tuple((1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t ** 2 * c + t ** 3 * d
                  for a, b, c, d in zip(p0, p1, p2, p3))
            for t in (step / steps for step in range(steps + 1))]


def toward(point, angle, along, side=0):
    """Return the point `along` in direction `angle` from `point`, shifted `side` to its left."""
    return (point[0] + cos(angle) * along - sin(angle) * side,
            point[1] + sin(angle) * along + cos(angle) * side)


def petal(base, angle, length, width):
    """Return the outline of a pointed petal or leaf growing from `base` at `angle`."""
    tip = toward(base, angle, length)
    return (cubic(base, toward(base, angle, length * 0.3, width), toward(base, angle, length * 0.8, width * 0.6), tip)
            + cubic(tip, toward(base, angle, length * 0.8, -width * 0.6), toward(base, angle, length * 0.3, -width),
                    base)[1:])


def circle(center, radius, steps=18):
    return [toward(center, 2 * pi * step / steps, radius) for step in range(steps)]


def ellipse(center, rx, ry, steps=24):
    return [(center[0] + rx * cos(2 * pi * step / steps), center[1] + ry * sin(2 * pi * step / steps))
            for step in range(steps)]


def scaled(center, size, points):
    """Return `points`, given in units of `size` around `center`, in inches."""
    return [(center[0] + x * size, center[1] + y * size) for x, y in points]


def upright(shapes, pivot):
    """Return `shapes` marked to stay upright in every corner, moved about `pivot` instead of mirrored."""
    return [(kind, color, points, pivot) for kind, color, points in shapes]


def tendril(start, angle, size, turns=1.4):
    """Return a curling tendril that leaves `start` heading along `angle` and spirals in."""
    center = toward(start, angle + pi / 2, size)
    return [toward(center, angle - pi / 2 + t * turns * 2 * pi, size * (1 - 0.8 * t))
            for t in (step / 24 for step in range(25))]


def spoke(center, angle, start, end):
    return [toward(center, angle, start), toward(center, angle, end)]


# Right half of a sugar-maple leaf as (angle from the leaf's axis in degrees, radius as a fraction of
# the leaf's length), from the stem round to the top lobe: three broad toothed lobes and a small one
# near the stem, with moderate notches between them.
MAPLE = [(180, 0.12), (160, 0.2), (145, 0.3), (128, 0.4), (115, 0.36), (105, 0.38), (95, 0.3), (85, 0.42),
         (75, 0.5), (70, 0.58), (60, 0.6), (52, 0.66), (45, 0.58), (40, 0.6), (33, 0.46), (25, 0.36),
         (18, 0.52), (13, 0.6), (8, 0.58), (0, 0.7)]


def maple_leaf(base, angle, length):
    """Return a maple-leaf outline whose stem joins at `base` and whose top lobe points at `angle`."""
    center = toward(base, angle, 0.35 * length)
    right = [toward(center, angle + degrees * pi / 180, radius * length) for degrees, radius in MAPLE]
    left = [toward(center, angle - degrees * pi / 180, radius * length) for degrees, radius in reversed(MAPLE[1:-1])]
    return right + left


def holly_leaf(base, angle, length, width, spines=3):
    """Return a spiky holly-leaf outline from `base` toward `angle`.

    Sharp spines sit on an oval outline, and each edge between two spines
    curves in toward the midrib.
    """
    def edge(side):
        # Spine positions as (fraction along the leaf, side offset), from the stem to the tip.
        stops = [(0, 0)] + [(f, side * width * sin(pi * f)) for f in (n / (spines + 1) for n in range(1, spines + 1))]
        stops.append((1, 0))
        points = []
        for (a0, s0), (a1, s1) in zip(stops, stops[1:]):
            inward = [(a0 + (a1 - a0) * t, (s0 + (s1 - s0) * t) * 0.55) for t in (0.3, 0.7)]
            points += cubic((a0, s0), *inward, (a1, s1), steps=6)[:-1]
        return points + [stops[-1]]
    return [toward(base, angle, a * length, s) for a, s in edge(1) + edge(-1)[::-1][1:-1]]


def firework(center, radius, colors, core, streaks=16):
    """Return a burst: tapered streaks in alternating `colors`, a spark at each tip, and a `core` glow.

    The first color's streaks start near the center and stop short; the
    second's start farther out and reach `radius`, so the burst has two
    rings. One streak points along the diagonal, so the burst mirrors onto
    itself.
    """
    shapes = []
    for index in range(streaks):
        angle, color = index * 2 * pi / streaks, colors[index % 2]
        start, end = (0.15, 0.68) if index % 2 == 0 else (0.42, 1.0)
        streak = petal(toward(center, angle, radius * start), angle, radius * (end - start - 0.1), radius * 0.06)
        shapes += [("fill", color, streak),
                   ("fill", color, circle(toward(center, angle, radius * end), radius * 0.065, steps=10))]
    shapes += [("line", core, spoke(center, pi / 8 + index * pi / 4, radius * 0.04, radius * 0.13)) for index in range(8)]
    return shapes


# Right half of a bat as (across, down) fractions of its wingspan, from between the ears over the ear,
# along the raised leading edge to the wing tip, then back along three scalloped "fingers" to the tail.
BAT = [(0.0, -0.06), (0.035, -0.13), (0.06, -0.06), (0.12, -0.08), (0.25, -0.16), (0.38, -0.16), (0.5, -0.08),
       (0.45, 0.04), (0.39, 0.0), (0.33, 0.1), (0.26, 0.04), (0.19, 0.12), (0.12, 0.05), (0.06, 0.12), (0.0, 0.16)]


def bat(center, span, tilt=0):
    """Return a bat silhouette with wings spread across `span`, turned by `tilt`."""
    right = [toward(center, tilt, across * span, down * span) for across, down in BAT]
    left = [toward(center, tilt, -across * span, down * span) for across, down in reversed(BAT[1:-1])]
    return right + left


# Jack-o'-lantern face cut-outs, in units of the pumpkin's width around its center (y points down).
JACK_EYES = ([(-0.22, -0.04), (-0.06, -0.04), (-0.14, -0.18)], [(0.06, -0.04), (0.22, -0.04), (0.14, -0.18)])
JACK_NOSE = [(-0.04, 0.04), (0.04, 0.04), (0.0, -0.03)]
JACK_MOUTH = [(-0.26, 0.08), (-0.14, 0.13), (-0.1, 0.08), (-0.05, 0.14), (0.05, 0.14), (0.1, 0.08), (0.14, 0.13),
              (0.26, 0.08), (0.17, 0.22), (0.06, 0.26), (0.03, 0.2), (-0.03, 0.2), (-0.06, 0.26), (-0.17, 0.22)]


def jack_o_lantern(center, size):
    """Return an upright carved pumpkin `size` wide: three lobes, a stem, and a face."""
    orange, light, carved, stem = (214, 118, 40), (232, 148, 62), (60, 36, 22), (104, 82, 52)
    lobes = [("fill", color, ellipse((center[0] + shift * size, center[1]), 0.3 * size, height * size))
             for shift, height, color in ((-0.2, 0.36, orange), (0.2, 0.36, orange), (0, 0.4, light))]
    stalk = [("fill", stem, scaled(center, size, [(-0.05, -0.36), (0.05, -0.36), (0.09, -0.5), (0.0, -0.53)]))]
    face = [("fill", carved, scaled(center, size, points)) for points in (*JACK_EYES, JACK_NOSE, JACK_MOUTH)]
    return upright(lobes + stalk + face, center)


def star(center, outer, spikes=5):
    return [toward(center, -pi / 2 + step * pi / spikes, outer if step % 2 == 0 else outer * 0.45)
            for step in range(2 * spikes)]


def both_edges(shapes):
    """Return `shapes` along the top edge, plus their mirror down the side edge."""
    return shapes + [(kind, color, [(v, u) for u, v in points]) for kind, color, points in shapes]


VINE = cubic((0.45, 0.36), (0.8, 0.24), (1.15, 0.44), (1.6, 0.32))


def spring():
    sage, rose = (138, 160, 132), (204, 150, 158)
    edge = [("line", sage, VINE)] + [("outline", sage, petal(VINE[step], angle, 0.13, 0.035))
                                     for step, angle in ((4, -0.9), (7, 0.9), (10, -0.8))]
    flower = [("outline", rose, petal(CORNER, INWARD + index * 2 * pi / 5, 0.11, 0.04)) for index in range(5)]
    return both_edges(edge) + flower + [("fill", sage, circle(CORNER, 0.022))]


def summer():
    sun, sea = (226, 176, 60), (96, 160, 176)
    wave = (cubic((0.48, 0.32), (0.66, 0.22), (0.84, 0.42), (1.02, 0.32))
            + cubic((1.02, 0.32), (1.2, 0.22), (1.38, 0.42), (1.56, 0.32))[1:])
    edge = [("line", sea, wave), ("line", sea, [(u, v + 0.08) for u, v in wave[4:-4]])]
    rays = [("line", sun, spoke(CORNER, pi / 8 + index * pi / 4, 0.085, 0.13)) for index in range(8)]
    return both_edges(edge) + [("outline", sun, circle(CORNER, 0.06))] + rays


def fall():
    twig, rust, gold, brown = (128, 96, 70), (196, 98, 52), (214, 158, 58), (150, 84, 50)
    # The leaves hang from the twig: the margin has more room below the twig than above it.
    edge = [("line", twig, VINE)]
    for (step, angle), color in zip(((3, 0.5), (6, 1.1), (9, 0.7), (11, 1.0)), (rust, gold, brown, rust)):
        edge.append(("fill", color, maple_leaf(VINE[step], angle, 0.12)))
    # The stem points at the page corner.
    base = toward(CORNER, INWARD + pi, 0.05)
    leaf = [("fill", rust, maple_leaf(base, INWARD, 0.21)), ("line", twig, spoke(base, INWARD, -0.05, 0.06))]
    return both_edges(edge) + leaf


def halloween():
    """A jack-o'-lantern in the corner, and a curling pumpkin vine with a small one at its end."""
    vine_green, leaf_green, purple = (88, 128, 70), (110, 150, 84), (70, 50, 90)
    vine = cubic((0.5, 0.36), (0.8, 0.25), (1.1, 0.44), (1.42, 0.34))
    edge = [("line", vine_green, vine), ("fill", leaf_green, maple_leaf(vine[4], 1.0, 0.12)),
            ("fill", leaf_green, maple_leaf(vine[9], 0.7, 0.11)),
            ("line", vine_green, tendril(vine[6], -0.9, 0.025)), ("line", vine_green, tendril(vine[11], 0.9, 0.022))]

    def figures(place):
        return [("fill", purple, bat(place(0.98, 0.28), 0.13, 0.15))] + jack_o_lantern(place(1.54, 0.35), 0.12)

    return (both_edges(edge) + figures(lambda u, v: (u, v)) + figures(lambda u, v: (v, u))
            + jack_o_lantern((0.36, 0.37), 0.26))


def snowflake(center, radius, color):
    shapes = []
    for index in range(6):
        angle = INWARD + index * pi / 3
        shapes.append(("line", color, spoke(center, angle, 0, radius)))
        fork = toward(center, angle, radius * 0.6)
        shapes += [("line", color, spoke(fork, angle + side, 0, radius * 0.35)) for side in (-0.8, 0.8)]
    return shapes


def winter():
    ice = (112, 150, 190)
    edge = []
    for center, radius in (((0.72, 0.31), 0.05), ((1.02, 0.38), 0.035), ((1.3, 0.31), 0.045), ((1.56, 0.37), 0.03)):
        edge += snowflake(center, radius, ice)
    edge += [("fill", ice, circle(center, 0.012)) for center in ((0.88, 0.25), (1.17, 0.43), (1.45, 0.25))]
    return both_edges(edge) + snowflake(CORNER, 0.12, ice)


def easter():
    sage, egg, pink, yellow, blue = (138, 160, 132), (160, 132, 196), (220, 150, 180), (225, 192, 90), (130, 170, 210)
    edge = [("line", sage, VINE)] + [("outline", sage, petal(VINE[step], angle, 0.12, 0.035))
                                     for step, angle in ((5, -0.9), (10, 0.9))]
    edge += [("fill", color, circle(VINE[step], 0.022)) for step, color in ((3, pink), (7, yellow), (12, blue))]
    # The narrow end of the egg points at the page corner.
    center = toward(CORNER, INWARD, 0.02)
    outline = [toward(center, INWARD, 0.085 * cos(t), 0.06 * sin(t) * (1 + 0.18 * cos(t)))
               for t in (2 * pi * step / 36 for step in range(36))]
    zigzag = [toward(center, INWARD, 0.012 * (-1) ** step, -0.058 + step * 0.0145) for step in range(9)]
    dots = [("fill", yellow, circle(toward(center, INWARD, 0.045, side), 0.01)) for side in (-0.025, 0, 0.025)]
    return both_edges(edge) + [("outline", egg, outline), ("line", pink, zigzag)] + dots


def july4():
    red, blue, gold = (190, 60, 60), (60, 90, 160), (220, 170, 60)
    edge = ([("fill", red, star((0.7, 0.33), 0.055))] + firework((0.98, 0.34), 0.07, (blue, red), gold, streaks=8)
            + [("fill", blue, star((1.24, 0.31), 0.045))] + firework((1.5, 0.35), 0.055, (red, blue), gold, streaks=8))
    return both_edges(edge) + firework(CORNER, 0.125, (red, blue), gold)


def thanksgiving():
    orange, light, stem, gold, leaf = (206, 116, 50), (232, 152, 82), (120, 92, 64), (192, 154, 78), (110, 140, 90)
    stalk = cubic((0.48, 0.36), (0.8, 0.3), (1.2, 0.38), (1.58, 0.32))
    edge = [("line", gold, stalk)]
    edge += [("fill", gold, petal(stalk[step], side, 0.07, 0.022)) for step in range(7, 12) for side in (-0.55, 0.55)]
    # The stem points at the page corner.
    center = toward(CORNER, INWARD, 0.04)
    # Side lobes first, so the lighter middle lobe sits in front of them.
    lobes = [("fill", color, [toward(toward(center, INWARD, 0, shift), INWARD, height * cos(t), width * sin(t))
                              for t in (2 * pi * step / 24 for step in range(24))])
             for shift, width, height, color in ((-0.045, 0.058, 0.072, orange), (0.045, 0.058, 0.072, orange),
                                                 (0, 0.055, 0.08, light))]
    tip = toward(center, INWARD + pi, 0.13)
    return both_edges(edge) + lobes + [
        ("line", stem, spoke(center, INWARD + pi, 0.078, 0.13)),
        ("fill", leaf, petal(toward(center, INWARD + pi, 0.1), INWARD + pi - 1.3, 0.06, 0.02)),
        ("fill", stem, petal(tip, INWARD + 0.3, 0.02, 0.008))]


def christmas():
    green, wire, red, gold, blue, out = (60, 112, 72), (90, 110, 90), (190, 50, 50), (220, 170, 60), (70, 110, 170), (45, 45, 45)
    # The wire leaves the holly in a gentle S-bend, like the vines of the other themes.
    lights = cubic((0.45, 0.33), (0.8, 0.22), (1.15, 0.44), (1.58, 0.31), steps=27)
    edge = [("line", wire, lights)]
    # Eight bulbs, clear of the holly, alternately hanging below the wire and standing above it.
    # The sixth one is burnt out.
    edge += [("fill", out if index == 5 else (red, gold, green, blue)[index % 4],
              petal(lights[step], pi / 2 * (-1) ** index, 0.055, 0.019))
             for index, step in enumerate(range(3, 27, 3))]
    holly = [("fill", green, holly_leaf(toward(CORNER, INWARD, 0.015), INWARD + turn, 0.17, 0.045))
             for turn in (-0.65, 0.65)]
    berries = [("fill", red, circle(toward(CORNER, INWARD + turn, 0.025), 0.02)) for turn in (pi, pi / 2, -pi / 2)]
    return both_edges(edge) + holly + berries


THEMES = {name: build() for name, build in (("spring", spring), ("summer", summer), ("fall", fall),
                                            ("winter", winter), ("easter", easter), ("july4", july4),
                                            ("halloween", halloween), ("thanksgiving", thanksgiving),
                                            ("christmas", christmas))}
SEASONS = {1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring", 6: "summer", 7: "summer",
           8: "summer", 9: "fall", 10: "fall", 11: "fall", 12: "winter"}
HOLIDAYS = {7: "july4", 10: "halloween", 11: "thanksgiving", 12: "christmas"}


def easter_date(year):
    """Return Western Easter Sunday: the anonymous Gregorian algorithm (Meeus, Jones, Butcher)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741 (the algorithm's own name)
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def theme_for(month):
    """Return the theme name for `month`: a holiday, else the season."""
    if month.month == easter_date(month.year).month:
        return "easter"
    return HOLIDAYS.get(month.month, SEASONS[month.month])
