"""The skeleton of the tree: where each person and each union is placed.

Nothing is positioned by hand. The rules, from section 4.2 of the plan:

- time runs from top to bottom: one band per generation;
- inside a band, older people are higher than younger ones;
- a union is a node of its own, placed between the two partners; the children
  hang from the union, not from a person;
- people are ordered so that lines cross as little as possible.

This module only decides positions (the "skeleton"). How things are drawn
(colours, sizes, line styles: the "skin") is in tree_skin.py, so the style
can change without touching these rules.

How the horizontal positions are found: partners who share a band form a
block that moves as one piece. Each block is pulled towards the unions of its
parents (above) and towards its children (below). The bands are swept several
times, top to bottom and back, each time sorting the blocks by where they are
pulled to and then spreading them so that nobody overlaps.
"""
from dataclasses import dataclass, field

from .kinship import CENTER, FamilyGraph, UnionRecord

# Horizontal distances.
UNION_GAP = 26  # room between two people of the same block, for the union node
BLOCK_GAP = 20  # room between neighbouring blocks
LONE_PARENT_ROOM = 26  # room beside a lone parent, for the union node

# Vertical distances, from the top of a band downwards.
ARC_ZONE = 24  # where unions that jump over someone are drawn
NODE_RADIUS = 26  # the largest circle
AGE_RANGE = 34  # how far the birth year can push a person down
LABEL_ZONE = 42  # the name under the circle
CHANNEL = 62  # between two bands: where the lines to the children travel

BAND_HEIGHT = ARC_ZONE + 2 * NODE_RADIUS + AGE_RANGE + LABEL_ZONE
BAND_PITCH = BAND_HEIGHT + CHANNEL
MARGIN = 40

SWEEPS = 8  # times the bands are re-sorted
SETTLING_ROUNDS = 6  # final rounds that only adjust positions


@dataclass
class PersonPlace:
    id: str
    x: float
    y: float
    layer: int  # index of the band, 0 at the top


@dataclass
class UnionPlace:
    record: UnionRecord
    x: float
    y: float
    layer: int
    # True when the union node sits right between (or beside) its partners;
    # False when the line to one partner has to jump over other people.
    is_direct: bool
    anchor: str  # the partner the node is next to
    lane: int = 0  # height of the jump, so that two jumps do not coincide


@dataclass
class Band:
    layer: int
    top: float
    bottom: float

    @property
    def arc_y(self) -> float:
        """Height at which jumping unions travel, above the circles."""
        return self.top + ARC_ZONE / 2

    @property
    def channel_y(self) -> float:
        """Middle of the free strip below this band."""
        return self.bottom + CHANNEL / 2


@dataclass
class TreeLayout:
    people: dict[str, PersonPlace] = field(default_factory=dict)
    unions: list[UnionPlace] = field(default_factory=list)
    bands: list[Band] = field(default_factory=list)
    left: float = 0
    right: float = 0
    top: float = 0
    bottom: float = 0
    union_gap: float = UNION_GAP

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top


class _Block:
    """Partners who share a band: they are laid out side by side as one piece."""

    def __init__(self, members: list[str], widths: dict[str, float]):
        self.members = members
        self.widths = widths
        self.x = 0.0
        self.offsets: dict[str, float] = {}
        self.width = 0.0
        self._measure()

    def _measure(self) -> None:
        self.width = sum(self.widths[m] for m in self.members)
        self.width += UNION_GAP * (len(self.members) - 1)
        position = -self.width / 2
        for member in self.members:
            self.offsets[member] = position + self.widths[member] / 2
            position += self.widths[member] + UNION_GAP

    def mirror(self) -> None:
        self.members.reverse()
        self._measure()


def _spread(targets: list[float], gaps: list[float]) -> list[float]:
    """Positions as close as possible to the targets, in the same order and
    at least `gaps[i]` apart (isotonic regression, "pool adjacent violators").
    """
    shifts = [0.0]
    for gap in gaps:
        shifts.append(shifts[-1] + gap)
    blocks: list[list[float]] = []  # [sum of values, count]
    for target, shift in zip(targets, shifts):
        blocks.append([target - shift, 1])
        while len(blocks) > 1 and (
            blocks[-2][0] / blocks[-2][1] > blocks[-1][0] / blocks[-1][1]
        ):
            total, count = blocks.pop()
            blocks[-1][0] += total
            blocks[-1][1] += count
    values: list[float] = []
    for total, count in blocks:
        values += [total / count] * int(count)
    return [value + shift for value, shift in zip(values, shifts)]


class _Skeleton:
    def __init__(self, graph, central, birth_years, widths):
        self.graph = graph
        self.central = central if central in set(graph.people) else None
        self.birth_years = birth_years
        self.order = {person: index for index, person in enumerate(graph.people)}
        self.lone_unions: dict[str, list[UnionRecord]] = {}
        for union in graph.unions:
            if len(union.partners) == 1:
                self.lone_unions.setdefault(union.partners[0], []).append(union)
        # A lone parent needs room beside the circle for the union node.
        self.widths = {
            person: widths[person] + (2 * LONE_PARENT_ROOM if person in self.lone_unions else 0)
            for person in graph.people
        }
        self.layer: dict[str, int] = {}
        self.block_of: dict[str, _Block] = {}
        self.rows: list[list[_Block]] = []

    # ----- Bands -------------------------------------------------------------

    def _assign_layers(self) -> None:
        """Give every person a band, including people with no link to the centre."""
        generation: dict[str, int] = {}
        if self.central:
            generation.update(self.graph.generations(self.central))
        for person in self.graph.people:
            if person in generation:
                continue
            group = self.graph.generations(person)
            shift = self._best_shift(group, generation)
            generation.update({member: value + shift for member, value in group.items()})
        # A child must be below both parents. When the parents are from
        # different generations (an uncle with his niece, say), the counted
        # generation may follow the upper parent: push the child down, and
        # its descendants with it. The admin forbids cycles, so this ends.
        changed = True
        while changed:
            changed = False
            for person in self.graph.people:
                parents = [parent.person for parent in self.graph.parents(person)]
                lowest_parent = max((generation[p] for p in parents), default=None)
                if lowest_parent is not None and generation[person] <= lowest_parent:
                    generation[person] = lowest_parent + 1
                    changed = True
        if generation:
            lowest = min(generation.values())
            self.layer = {person: value - lowest for person, value in generation.items()}

    def _best_shift(self, group: dict[str, int], placed: dict[str, int]) -> int:
        """Where to put a separate group of relatives: in the bands whose
        people were born around the same years."""
        if not placed:
            return 0
        years_by_generation: dict[int, list[int]] = {}
        for person, value in placed.items():
            if self.birth_years.get(person):
                years_by_generation.setdefault(value, []).append(self.birth_years[person])
        average = {value: sum(years) / len(years) for value, years in years_by_generation.items()}
        dated = [(value, self.birth_years[p]) for p, value in group.items() if self.birth_years.get(p)]

        low, high = min(placed.values()), max(placed.values())
        group_low, group_high = min(group.values()), max(group.values())
        best_shift, best_cost = -group_high, None  # default: youngest beside the centre
        for shift in range(low - group_high, high - group_low + 1):
            costs = [abs(year - average[value + shift]) for value, year in dated if value + shift in average]
            if not costs:
                continue
            cost = sum(costs) / len(costs)
            if best_cost is None or cost < best_cost:
                best_shift, best_cost = shift, cost
        return best_shift

    # ----- Blocks ------------------------------------------------------------

    def _build_blocks(self) -> None:
        """Group partners of the same band into blocks, in a first rough order."""
        links: dict[str, list[str]] = {person: [] for person in self.graph.people}
        for union in self.graph.unions:
            if len(union.partners) == 2:
                first, second = union.partners
                if self.layer[first] == self.layer[second]:
                    if second not in links[first]:
                        links[first].append(second)
                        links[second].append(first)

        rank = self._side_ranks()
        layer_count = max(self.layer.values(), default=-1) + 1
        self.rows = [[] for _ in range(layer_count)]
        seen: set[str] = set()
        for person in self.graph.people:
            if person in seen:
                continue
            group = self._linked_group(person, links)
            seen |= set(group)
            block = _Block(self._line_up(group, links), self.widths)
            for member in block.members:
                self.block_of[member] = block
            self.rows[self.layer[person]].append(block)

        def birth_position(block: _Block) -> int:
            # A couple takes the place of the one born into the family, so a
            # sibling's older husband does not push her out of birth order.
            born_here = [m for m in block.members if self.graph.parent_unions(m)]
            return min(self.order[m] for m in born_here or block.members)

        for row in self.rows:
            row.sort(
                key=lambda block: (
                    sum(rank[m] for m in block.members) / len(block.members),
                    birth_position(block),
                )
            )
            # Equal targets: the row is packed tightly and centred on zero.
            self._place_row(row, [0.0] * len(row))

    def _side_ranks(self) -> dict[str, int]:
        """Rough left-to-right order: first side, the centre, the other sides."""
        rank = {person: 99 for person in self.graph.people}
        if not self.central:
            return rank
        figures = self.graph.parental_figures(self.central)
        positions = {CENTER: 1}
        for index, figure in enumerate(figures):
            positions[figure] = 0 if index == 0 else index + 1
        for person, side in self.graph.sides(self.central).items():
            rank[person] = positions[side]
        return rank

    def _linked_group(self, start: str, links: dict[str, list[str]]) -> list[str]:
        group, queue = [start], [start]
        while queue:
            for partner in links[queue.pop()]:
                if partner not in group:
                    group.append(partner)
                    queue.append(partner)
        return group

    def _line_up(self, group: list[str], links: dict[str, list[str]]) -> list[str]:
        """Order of a block.

        A couple: the one whose parents are in the tree comes first, so the
        partner "from outside" is on the same side in every couple. Someone
        with several unions stays in the middle, with the first partner on
        one side and the later partners on the other.
        """
        hub = max(
            group,
            key=lambda person: (
                len(links[person]),
                bool(self.graph.parent_unions(person)),
                -self.order[person],
            ),
        )
        visited = {hub}

        def chain(person: str) -> list[str]:
            visited.add(person)
            line = [person]
            for partner in links[person]:
                if partner not in visited:
                    line += chain(partner)
            return line

        left: list[str] = []
        right: list[str] = []
        several_unions = len(links[hub]) > 1
        for index, partner in enumerate(links[hub]):
            if partner in visited:
                continue
            if index == 0 and several_unions:
                left = list(reversed(chain(partner)))
            else:
                right += chain(partner)
        return left + [hub] + right

    # ----- Positions ---------------------------------------------------------

    def _x(self, person: str) -> float:
        block = self.block_of[person]
        return block.x + block.offsets[person]

    def _union_anchor(self, union: UnionRecord) -> tuple[str, float, bool]:
        """Where the node of a union is: (partner it is next to, x, is_direct)."""
        if len(union.partners) == 1:
            person = union.partners[0]
            # The circle keeps the middle of the widened slot; the node goes right.
            return person, self._x(person) + self.widths[person] / 2 - LONE_PARENT_ROOM / 2, True

        first, second = union.partners
        if self.layer[first] != self.layer[second]:
            lower = first if self.layer[first] > self.layer[second] else second
            return lower, self._x(lower) + self.widths[lower] / 2 + UNION_GAP / 2, False

        block = self.block_of[first]
        positions = (block.members.index(first), block.members.index(second))
        if abs(positions[0] - positions[1]) == 1:
            left, right = (first, second) if positions[0] < positions[1] else (second, first)
            edge_left = self._x(left) + self.widths[left] / 2
            edge_right = self._x(right) - self.widths[right] / 2
            return left, (edge_left + edge_right) / 2, True

        # The partners are not neighbours: the node sits beside the one with
        # fewer unions, on the side that faces the other partner.
        unions_of = {person: len(self.graph.unions_of(person)) for person in union.partners}
        far = min(union.partners, key=lambda person: (unions_of[person], -self.order[person]))
        other = second if far == first else first
        direction = 1 if self._x(other) > self._x(far) else -1
        return far, self._x(far) + direction * (self.widths[far] / 2 + UNION_GAP / 2), False

    def _union_x(self, union: UnionRecord) -> float:
        return self._union_anchor(union)[1]

    def _pulls(self, block: _Block, use_parents: bool, use_children: bool) -> list[tuple[float, float]]:
        """Everything pulling a block sideways: (where to, offset inside the block)."""
        pulls = []
        if use_parents:
            for member in block.members:
                parent_unions = self.graph.parent_unions(member)
                if parent_unions:
                    target = sum(self._union_x(u) for u in parent_unions) / len(parent_unions)
                    pulls.append((target, block.offsets[member]))
        if use_children:
            for member in block.members:
                for union in self.graph.unions_of(member):
                    anchor, x, _direct = self._union_anchor(union)
                    if anchor != member or not union.children:
                        continue
                    children_x = [self._x(child) for child, _kind in union.children]
                    pulls.append((sum(children_x) / len(children_x), x - block.x))
        return pulls

    def _place_row(self, row: list[_Block], targets: list[float]) -> None:
        """Put each block as close to its target as the others allow."""
        if not row:
            return
        gaps = [(a.width + b.width) / 2 + BLOCK_GAP for a, b in zip(row, row[1:])]
        for block, position in zip(row, _spread(targets, gaps)):
            block.x = position

    def _has_parents(self, block: _Block) -> bool:
        return any(self.graph.parent_unions(member) for member in block.members)

    def _sweep_row(self, row: list[_Block], use_parents: bool, use_children: bool, reorder: bool) -> None:
        keyed = []
        for block in row:
            pulls = self._pulls(block, use_parents, use_children)
            # The order of a block is decided by its parents: siblings stay in
            # birth order. Only blocks without parents in the tree (the oldest
            # ancestors, for example) are ordered by where their children are.
            fixed = not use_parents and self._has_parents(block)
            if fixed:
                keyed.append((block.x, self._target(pulls, block.x), block))
                continue
            if reorder and len(block.members) > 1 and pulls:
                # Try the block the other way round and keep the better fit.
                cost = self._misfit(pulls)
                block.mirror()
                mirrored = self._pulls(block, use_parents, use_children)
                if self._misfit(mirrored) < cost - 0.001:
                    pulls = mirrored
                else:
                    block.mirror()
            sort_key = sum(to for to, _offset in pulls) / len(pulls) if pulls else block.x
            keyed.append((sort_key, self._target(pulls, block.x), block))
        if reorder:
            keyed.sort(key=lambda item: item[0])  # stable: ties keep their order
            row[:] = [block for _key, _target, block in keyed]
        self._place_row(row, [target for _key, target, _block in keyed])

    @staticmethod
    def _target(pulls: list[tuple[float, float]], current: float) -> float:
        """Where the centre of a block should go to satisfy its pulls."""
        if not pulls:
            return current
        return sum(to - offset for to, offset in pulls) / len(pulls)

    @staticmethod
    def _misfit(pulls: list[tuple[float, float]]) -> float:
        """How badly a block fits its pulls once centred on them."""
        centre = sum(to - offset for to, offset in pulls) / len(pulls)
        return sum(abs(to - (centre + offset)) for to, offset in pulls)

    def _settle(self) -> None:
        last = len(self.rows) - 1
        for _ in range(SWEEPS):
            for index in range(1, last + 1):
                self._sweep_row(self.rows[index], True, False, reorder=True)
            for index in range(last - 1, -1, -1):
                self._sweep_row(self.rows[index], False, True, reorder=True)
        for _ in range(SETTLING_ROUNDS):
            for index in range(0, last + 1):
                self._sweep_row(self.rows[index], True, True, reorder=False)
            for index in range(last, -1, -1):
                self._sweep_row(self.rows[index], True, True, reorder=False)

    # ----- Heights -----------------------------------------------------------

    def _heights(self) -> dict[str, float]:
        """Height of each person inside the band: older people higher."""
        heights = {}
        for index, row in enumerate(self.rows):
            members = [member for block in row for member in block.members]
            years = [self.birth_years[m] for m in members if self.birth_years.get(m)]
            oldest, youngest = (min(years), max(years)) if years else (0, 0)
            share: dict[str, float] = {}
            for member in members:
                year = self.birth_years.get(member)
                if year and youngest > oldest:
                    share[member] = (year - oldest) / (youngest - oldest)
            for member in members:
                if member not in share:
                    # Unknown year: beside the partners, or in the middle.
                    known = [share[m] for m in self.block_of[member].members if m in share]
                    share[member] = sum(known) / len(known) if known else 0.5
            band_top = index * BAND_PITCH
            for member in members:
                heights[member] = band_top + ARC_ZONE + NODE_RADIUS + share[member] * AGE_RANGE
        return heights

    # ----- Result ------------------------------------------------------------

    def build(self) -> TreeLayout:
        layout = TreeLayout()
        if not self.graph.people:
            return layout
        self._assign_layers()
        self._build_blocks()
        self._settle()
        heights = self._heights()

        for person in self.graph.people:
            layout.people[person] = PersonPlace(
                person, round(self._x(person), 2), round(heights[person], 2), self.layer[person]
            )
        layout.bands = [
            Band(index, index * BAND_PITCH, index * BAND_PITCH + BAND_HEIGHT)
            for index in range(len(self.rows))
        ]

        lanes: dict[int, int] = {}
        taken: dict[tuple[int, int], int] = {}
        for union in self.graph.unions:
            anchor, x, is_direct = self._union_anchor(union)
            layer = self.layer[anchor]
            if is_direct and len(union.partners) == 2:
                y = sum(heights[p] for p in union.partners) / 2
            else:
                y = heights[anchor]
            # Two nodes in the same spot (rare): move the later one down a bit.
            spot = (layer, round(x))
            y += 14 * taken.get(spot, 0)
            taken[spot] = taken.get(spot, 0) + 1
            lane = 0
            if not is_direct:
                lane = lanes.get(layer, 0)
                lanes[layer] = lane + 1
            layout.unions.append(
                UnionPlace(union, round(x, 2), round(y, 2), layer, is_direct, anchor, lane)
            )

        edges_left = [p.x - self.widths[p.id] / 2 for p in layout.people.values()]
        edges_right = [p.x + self.widths[p.id] / 2 for p in layout.people.values()]
        layout.left = min(edges_left) - MARGIN
        layout.right = max(edges_right) + MARGIN
        layout.top = -MARGIN
        layout.bottom = layout.bands[-1].bottom + MARGIN
        return layout


def compute_layout(
    graph: FamilyGraph,
    central: str | None,
    birth_years: dict[str, int | None],
    widths: dict[str, float],
) -> TreeLayout:
    """Place everyone in the family.

    `central` is the person the tree is organised around (None is accepted),
    `birth_years` the year each person was born when known, and `widths` the
    horizontal room each person needs (circle and name).
    """
    return _Skeleton(graph, central, birth_years, widths).build()
