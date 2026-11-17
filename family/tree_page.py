"""Gathers everything the tree page shows: the drawing and its legend."""
from dataclasses import dataclass

from django.conf import settings
from django.urls import reverse

from .graph import load_family_graph
from .images import TREE, variant_url
from .models import Person, Union
from .tree_layout import compute_layout
from .tree_skin import (
    child_line_class,
    child_path,
    diamond_points,
    node_style,
    union_line_class,
    union_path,
)


@dataclass
class PersonDrawing:
    id: str
    url: str
    title: str
    css_class: str
    x: float
    y: float
    radius: float
    ring_radius: float
    fill: str
    stroke: str
    stroke_width: float
    font_size: float
    label: list[tuple[str, float]]  # (text, y of the line)
    photo: str  # address of a small round photo, or ""

    @property
    def photo_x(self) -> float:
        return round(self.x - self.radius, 2)

    @property
    def photo_y(self) -> float:
        return round(self.y - self.radius, 2)

    @property
    def photo_size(self) -> float:
        return 2 * self.radius


def build_tree_page() -> dict:
    """The values used by the template family/tree.html."""
    people = {person.identifier: person for person in Person.objects.all()}
    if not people:
        return {"tree": None}

    graph = load_family_graph()
    wanted_central = settings.RAIZES_CENTRAL_PERSON
    central = people.get(wanted_central)
    # Without a central person everybody is drawn at the same size.
    distances = graph.distances(central.identifier) if central else {i: 1 for i in people}

    styles = {
        identifier: node_style(
            person.given_name,
            person.surname,
            distances.get(identifier),
            person.is_deceased,
            person is central,
        )
        for identifier, person in people.items()
    }
    layout = compute_layout(
        graph,
        central.identifier if central else None,
        {identifier: person.birth_year for identifier, person in people.items()},
        {identifier: style.slot_width for identifier, style in styles.items()},
    )
    # Lines end at the centre of the circles, which are drawn over them.
    radii = {identifier: 0 for identifier in styles}

    drawings = []
    for identifier, place in layout.people.items():
        person, style = people[identifier], styles[identifier]
        css_class = "person"
        if person.is_deceased:
            css_class += " deceased"
        if person is central:
            css_class += " central"
        years = person.years_display
        ring_radius = style.radius + 5 if person is central else 0
        # The name starts below the circle (or below the outer ring).
        first_line = place.y + max(style.radius, ring_radius) + style.font_size + 4
        drawings.append(
            PersonDrawing(
                id=identifier,
                url=reverse("family:person_detail", args=[identifier]),
                title=f"{person.full_name} ({years})" if years else person.full_name,
                css_class=css_class,
                x=place.x,
                y=place.y,
                radius=style.radius,
                ring_radius=ring_radius,
                fill=style.fill,
                stroke=style.stroke,
                stroke_width=style.stroke_width,
                font_size=style.font_size,
                label=[
                    (line, round(first_line + index * style.font_size * 1.12, 1))
                    for index, line in enumerate(style.label_lines)
                ],
                photo=variant_url(person.photo.name, TREE) if person.photo else "",
            )
        )
    # Nearest people are drawn last, on top of the others.
    drawings.sort(key=lambda drawing: -drawing.radius)

    stored_unions = {union.pk: union for union in Union.objects.all()}
    union_lines, union_nodes, child_lines = [], [], []
    for node in layout.unions:
        union = stored_unions[node.record.id]
        if len(node.record.partners) == 2:
            css = union_line_class(union.kind, union.is_ended)
        else:
            css = "lone"
        union_lines.append((css, union_path(node, layout.people, radii, layout.bands)))
        union_nodes.append(diamond_points(node))
        for child, kind in node.record.children:
            child_lines.append(
                (
                    child_line_class(kind),
                    child_path(node, layout.people[child], radii[child], layout.bands[node.layer]),
                )
            )

    return {
        "tree": {
            "view_box": f"{layout.left:.0f} {layout.top:.0f} {layout.width:.0f} {layout.height:.0f}",
            "width": round(layout.width),
            "height": round(layout.height),
            # A faint stripe behind every other band helps to follow a generation.
            "bands": [
                (
                    round(layout.left),
                    round(band.top - 6),
                    round(layout.width),
                    round(band.bottom - band.top + 12),
                )
                for band in layout.bands
                if band.layer % 2 == 0
            ],
            "people": drawings,
            "union_lines": union_lines,
            "union_nodes": union_nodes,
            "child_lines": child_lines,
        },
        "central": central,
        "wanted_central": wanted_central,
    }
