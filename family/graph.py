"""Reads the database and builds the family graph used by the kinship rules."""
from .kinship import FamilyGraph, UnionRecord
from .models import ChildLink, Person, Union

# Unknown dates are sorted after every known date.
_UNKNOWN_DATE = "9999"


def load_family_graph() -> FamilyGraph:
    """Everyone and every union, people ordered by birth and unions by start."""
    people = sorted(
        Person.objects.values_list("identifier", "birth_date"),
        key=lambda row: (row[1] or _UNKNOWN_DATE, row[0]),
    )
    identifiers = [identifier for identifier, _birth in people]

    children: dict[int, list[tuple[str, str]]] = {}
    for union_id, child, kind in ChildLink.objects.values_list(
        "union_id", "child__identifier", "kind"
    ):
        children.setdefault(union_id, []).append((child, kind))

    unions = sorted(
        Union.objects.values_list(
            "id", "start_date", "partner1__identifier", "partner2__identifier"
        ),
        key=lambda row: (row[1] or _UNKNOWN_DATE, row[0]),
    )
    records = [
        UnionRecord(
            id=union_id,
            partners=tuple(partner for partner in (first, second) if partner),
            children=tuple(children.get(union_id, ())),
        )
        for union_id, _start, first, second in unions
    ]
    return FamilyGraph(identifiers, records)
