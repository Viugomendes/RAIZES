"""The skin of the tree: how people, unions and links are drawn.

This is the "first proof" of section 4.2 of the plan, a simple visual code:

    person            circle with the name
    central person    circle with a double ring
    deceased person   circle with only the outline
    union             small diamond between the two partners
    current union     thick solid line        ended union   dashed line
    dating            dotted line
    biological child  thin solid line         adoptive      dash-dot line
    foster child      thin dotted line
    side              one colour per parental figure of the central person
    distance          the further away, the lighter and the smaller

The positions come from tree_layout.py (the skeleton). Replacing this file by
another skin changes the look without touching the rules of position.
"""
from dataclasses import dataclass

from django.conf import settings

from .kinship import ADOPTIVE, CENTER, FOSTER
from .tree_layout import Band, PersonPlace, UnionPlace

# Side colours. These three were checked with a colour-blindness simulation
# (every pair stays distinguishable for protanopia and deuteranopia). No
# fourth colour passes that check against all three, so further sides share
# one neutral colour and are told apart by the legend and by position.
SIDE_COLORS = ["#2a78d6", "#eb6834", "#1baf7a"]
OTHER_SIDES_COLOR = "#8f7f9c"
CENTER_COLOR = "#3a3531"  # the central person, siblings, partners, descendants
UNLINKED_COLOR = "#b3aca3"  # people with no link to the central person
SURFACE = "#ffffff"

# By distance from the central person: 0, 1, 2, 3, 4 or more.
RADII = [26, 22, 19, 16, 13]
FONT_SIZES = [15, 14.5, 14, 13.5, 13]
FADES = [0.0, 0.0, 0.28, 0.46, 0.6]  # share of white mixed into the colour

DIAMOND = 6  # half of the diagonal of a union node
LABEL_CHAR_WIDTH = 0.6  # average width of a letter, in font sizes
SLOT_PADDING = 12


@dataclass(frozen=True)
class NodeStyle:
    radius: float
    font_size: float
    label_lines: list[str]
    slot_width: float  # horizontal room the person needs
    fill: str
    stroke: str
    stroke_width: float


def _mix_with_white(colour: str, share: float) -> str:
    channels = [int(colour[index : index + 2], 16) for index in (1, 3, 5)]
    mixed = [round(channel + (255 - channel) * share) for channel in channels]
    return "#{:02x}{:02x}{:02x}".format(*mixed)


def side_colors() -> list[str]:
    """The colours of the sides: the family's choice (RAIZES_SIDE_COLORS) or the default."""
    return list(getattr(settings, "RAIZES_SIDE_COLORS", None) or SIDE_COLORS)


def side_color(side: str | None, parental_figures: list[str]) -> str:
    """Base colour of a person from their side (None = no link to the centre)."""
    if side is None:
        return UNLINKED_COLOR
    if side == CENTER:
        return CENTER_COLOR
    index = parental_figures.index(side)
    colors = side_colors()
    return colors[index] if index < len(colors) else OTHER_SIDES_COLOR


def _step(distance: int | None) -> int:
    """Index in the tables above; unknown distance counts as the furthest."""
    last = len(RADII) - 1
    return last if distance is None else min(distance, last)


def node_style(
    given_name: str,
    surname: str,
    distance: int | None,
    colour: str,
    is_deceased: bool,
    is_central: bool,
) -> NodeStyle:
    step = _step(distance)
    radius = RADII[step]
    font_size = FONT_SIZES[step]
    shade = _mix_with_white(colour, FADES[step])

    label_lines = given_name.split()[:1] + surname.split()[-1:]
    longest = max((len(line) for line in label_lines), default=0)
    # The room is measured for the largest look a person can get, because
    # "see from..." in the browser can make anyone the central person
    # without moving anybody.
    label_width = longest * max(FONT_SIZES) * LABEL_CHAR_WIDTH
    slot_width = max(2 * (max(RADII) + 6), label_width) + SLOT_PADDING

    if is_deceased:
        # Only the outline: an empty circle drawn in the side's colour.
        return NodeStyle(radius, font_size, label_lines, slot_width, SURFACE, shade, 2.5)
    return NodeStyle(radius, font_size, label_lines, slot_width, shade, shade, 0)


def union_line_class(kind: str, is_ended: bool) -> str:
    if kind == "dating":
        return "dating"
    return "ended" if is_ended else "current"


def child_line_class(kind: str) -> str:
    if kind == ADOPTIVE:
        return "adoptive"
    if kind == FOSTER:
        return "foster"
    return "biological"


def _n(value: float) -> str:
    """A number for an SVG path: one decimal, no trailing zero."""
    return f"{value:.1f}".rstrip("0").rstrip(".")


def diamond_points(node: UnionPlace) -> str:
    x, y, d = node.x, node.y, DIAMOND
    return f"{_n(x)},{_n(y - d)} {_n(x + d)},{_n(y)} {_n(x)},{_n(y + d)} {_n(x - d)},{_n(y)}"


def union_path(
    node: UnionPlace,
    places: dict[str, PersonPlace],
    radii: dict[str, float],
    bands: list[Band],
) -> str:
    """The line between the partners of a union, passing through its node."""
    partners = [places[person] for person in node.record.partners]
    if len(partners) == 1:
        lone = partners[0]
        return f"M{_n(lone.x)},{_n(lone.y)} L{_n(node.x)},{_n(node.y)}"

    if node.is_direct:
        first, second = partners
        return (
            f"M{_n(first.x)},{_n(first.y)} L{_n(node.x)},{_n(node.y)} "
            f"L{_n(second.x)},{_n(second.y)}"
        )

    # The node is beside one partner; the line to the other one curves over
    # (or down to) whoever is in between.
    near = places[node.anchor]
    far = next(place for place in partners if place.id != node.anchor)
    path = f"M{_n(near.x)},{_n(near.y)} L{_n(node.x)},{_n(node.y)} "
    if far.layer == near.layer:
        start_y = far.y - radii[far.id]
        control_y = bands[near.layer].top - 6 - 12 * node.lane
    else:
        start_y = far.y + radii[far.id]
        control_y = (start_y + node.y) / 2
    path += (
        f"M{_n(far.x)},{_n(start_y)} C{_n(far.x)},{_n(control_y)} "
        f"{_n(node.x)},{_n(control_y)} {_n(node.x)},{_n(node.y - DIAMOND)}"
    )
    return path


def child_path(node: UnionPlace, child: PersonPlace, child_radius: float, band: Band) -> str:
    """The line from a union node down to a child.

    It drops straight down between the names of the partners, then curves
    through the free strip between the two bands to the top of the child.
    """
    start_y = node.y + DIAMOND
    drop_y = max(band.bottom, start_y)
    end_y = child.y - child_radius
    middle_y = (drop_y + end_y) / 2
    return (
        f"M{_n(node.x)},{_n(start_y)} L{_n(node.x)},{_n(drop_y)} "
        f"C{_n(node.x)},{_n(middle_y)} {_n(child.x)},{_n(middle_y)} "
        f"{_n(child.x)},{_n(end_y)}"
    )
