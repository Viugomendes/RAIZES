"""The kinship rules.

Nobody types who is whose parent, sibling or grandchild: everything is
calculated here from the unions and their children.

This module knows nothing about the database or the pages. It works on plain
identifiers (text), which keeps the rules easy to test and to reuse.
"""
from collections import deque
from collections.abc import Hashable, Iterable
from dataclasses import dataclass, field
from typing import NamedTuple

# Kinds of link between a child and a union, from strongest to weakest.
BIOLOGICAL = "biological"
ADOPTIVE = "adoptive"
FOSTER = "foster"
_STRENGTH = {BIOLOGICAL: 0, ADOPTIVE: 1, FOSTER: 2}

# The "side" of people who are not on the side of any single parent: the
# central person, their siblings, partners and descendants.
CENTER = "center"


@dataclass(frozen=True)
class UnionRecord:
    """A union as the rules see it."""

    id: Hashable
    partners: tuple[str, ...]  # one or two people
    children: tuple[tuple[str, str], ...] = ()  # (child, kind of link)


class Relative(NamedTuple):
    """A parent or a child, with the kind of link to them."""

    person: str
    kind: str


@dataclass(frozen=True)
class Siblings:
    full: list[str] = field(default_factory=list)  # children of the same union
    half: list[str] = field(default_factory=list)  # one parent in common
    step: list[str] = field(default_factory=list)  # linked only by who raised them

    @property
    def all(self) -> list[str]:
        return self.full + self.half + self.step


class FamilyGraph:
    """Everyone in the family and the unions between them.

    Lists are always returned in the order the people and the unions were
    given, so if people arrive ordered by birth, siblings come out oldest first.
    """

    def __init__(self, people: Iterable[str], unions: Iterable[UnionRecord]):
        self.people = list(people)
        self.unions = list(unions)
        self._order = {person: index for index, person in enumerate(self.people)}
        self._unions_as_partner: dict[str, list[UnionRecord]] = {p: [] for p in self.people}
        self._unions_as_child: dict[str, list[tuple[UnionRecord, str]]] = {
            p: [] for p in self.people
        }
        for union in self.unions:
            for partner in union.partners:
                self._unions_as_partner[partner].append(union)
            for child, kind in union.children:
                self._unions_as_child[child].append((union, kind))

    # ----- Direct relatives --------------------------------------------------

    def unions_of(self, person: str) -> list[UnionRecord]:
        """The unions in which the person is a partner."""
        return list(self._unions_as_partner[person])

    def partners(self, person: str) -> list[str]:
        """The known partners of the person, one per union."""
        found = []
        for union in self._unions_as_partner[person]:
            for partner in union.partners:
                if partner != person and partner not in found:
                    found.append(partner)
        return found

    def _strongest(self, links: Iterable[tuple[str, str]]) -> list[Relative]:
        """One entry per person, keeping the strongest kind of link."""
        best: dict[str, str] = {}
        for person, kind in links:
            if person not in best or _STRENGTH[kind] < _STRENGTH[best[person]]:
                best[person] = kind
        return [Relative(person, kind) for person, kind in best.items()]

    def parents(self, person: str) -> list[Relative]:
        """The parental figures: biological first, then adoptive, then foster."""
        links = [
            (partner, kind)
            for union, kind in self._unions_as_child[person]
            for partner in union.partners
        ]
        parents = self._strongest(links)
        parents.sort(key=lambda parent: (_STRENGTH[parent.kind], self._order[parent.person]))
        return parents

    def children(self, person: str) -> list[Relative]:
        """The children from every union of the person."""
        links = [
            link for union in self._unions_as_partner[person] for link in union.children
        ]
        children = self._strongest(links)
        children.sort(key=lambda child: self._order[child.person])
        return children

    def grandchildren(self, person: str) -> list[str]:
        found = {
            grandchild.person
            for child in self.children(person)
            for grandchild in self.children(child.person)
        }
        return sorted(found, key=self._order.__getitem__)

    def siblings(self, person: str) -> Siblings:
        """Full, half and step siblings. Each sibling is in exactly one group.

        - full: both are children of the same union, by blood or adoption;
        - half: they share a parent by blood or adoption, but not the union;
        - step: the only parent they share raised one of them (a stepfather's
          own child, for example).
        """
        own_unions = self._unions_as_child[person]
        own_family_unions = {union.id for union, kind in own_unions if kind != FOSTER}
        own_parents = {parent.person: parent.kind for parent in self.parents(person)}

        full, half, step = [], [], []
        for other in self.people:
            if other == person:
                continue
            other_parents = {parent.person: parent.kind for parent in self.parents(other)}
            shared = own_parents.keys() & other_parents.keys()
            if not shared:
                continue
            other_family_unions = {
                union.id for union, kind in self._unions_as_child[other] if kind != FOSTER
            }
            if own_family_unions & other_family_unions:
                full.append(other)
            elif any(own_parents[p] != FOSTER and other_parents[p] != FOSTER for p in shared):
                half.append(other)
            else:
                step.append(other)
        return Siblings(full, half, step)

    # ----- From a central person outwards ------------------------------------

    def parental_figures(self, central: str) -> list[str]:
        """The parents of the central person: each one starts a "side"."""
        return [parent.person for parent in self.parents(central)]

    def _steps(self, person: str) -> list[tuple[str, int]]:
        """Everyone one step away, with the change of generation.

        Blood links come before partners, so that when two paths have the
        same length the generation follows the blood link.
        """
        steps = [(parent.person, -1) for parent in self.parents(person)]
        steps += [(child.person, +1) for child in self.children(person)]
        steps += [(partner, 0) for partner in self.partners(person)]
        return steps

    def _walk(self, central: str):
        """Visit everyone linked to the central person, nearest first.

        Returns three dictionaries: distance, generation and the set of
        "first steps" (which neighbours of the central person the shortest
        paths go through).
        """
        distance = {central: 0}
        generation = {central: 0}
        first_steps: dict[str, set[str]] = {central: set()}
        queue = deque([central])
        while queue:
            person = queue.popleft()
            for neighbour, change in self._steps(person):
                via = {neighbour} if person == central else first_steps[person]
                if neighbour not in distance:
                    distance[neighbour] = distance[person] + 1
                    generation[neighbour] = generation[person] + change
                    first_steps[neighbour] = set(via)
                    queue.append(neighbour)
                elif distance[neighbour] == distance[person] + 1:
                    first_steps[neighbour] |= via  # another path, equally short
        return distance, generation, first_steps

    def distances(self, central: str) -> dict[str, int]:
        """How many steps separate each person from the central person.

        A step goes from a person to a parent, a child or a partner. People
        with no link to the central person are left out.
        """
        return self._walk(central)[0]

    def generations(self, central: str) -> dict[str, int]:
        """The generation of each person: 0 for the central person, -1 for
        parents and uncles, -2 for grandparents, +1 for children and nephews.

        Partners share a generation, whatever their ages.
        """
        return self._walk(central)[1]

    def sides(self, central: str) -> dict[str, str]:
        """Through which parental figure each person is linked to the centre.

        The value is the identifier of that parental figure. People whose
        shortest paths go through more than one parent (siblings), or through
        no parent at all (partner, children), get CENTER.
        """
        _distance, _generation, first_steps = self._walk(central)
        parental_figures = set(self.parental_figures(central))
        sides = {}
        for person, steps in first_steps.items():
            if len(steps) == 1 and steps <= parental_figures:
                sides[person] = next(iter(steps))
            else:
                sides[person] = CENTER
        return sides
