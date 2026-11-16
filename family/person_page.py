"""Gathers everything the page of a person shows.

The page has 10 sections. Section 1 (basic data) and section 10 (gallery and
places) are built by the site; sections 2 to 9 are the texts typed in the
admin. A section appears only when it has something to show.
"""
from dataclasses import dataclass, field

from django.utils.safestring import SafeString
from django.utils.translation import gettext as _

from .graph import load_family_graph
from .kinship import ADOPTIVE, FOSTER
from .markup import LinkTargets, render_text
from .models import TEXT_SECTIONS, Person, Union
from .youtube import embed_url, watch_url


@dataclass
class RelativeView:
    """A relative in a list, with a note when the link is not biological."""

    person: Person
    note: str = ""


@dataclass
class UnionView:
    partner: Person | None
    kind: str
    period: str
    is_ended: bool
    children: list[RelativeView]
    story: SafeString


@dataclass
class SectionView:
    key: str
    title: str
    html: SafeString
    stories: list[UnionView] = field(default_factory=list)


def link_note(kind: str) -> str:
    """Short note shown next to an adoptive or foster relative."""
    if kind == ADOPTIVE:
        return _("by adoption")
    if kind == FOSTER:
        return _("raised as family")
    return ""


def union_period(union: Union) -> str:
    """ "1992–2003", "since 2005", "until 2003" or nothing.

    A union that was never marked as ended still stops when one of the
    partners dies, so the year of the first death closes the period.
    """
    start_year = union.start.year if union.start else None
    end_year = union.end.year if union.end else None
    is_over = union.is_ended

    if end_year is None and not union.is_ended:
        deceased = [partner for partner in union.partners if partner.is_deceased]
        death_years = [partner.death.year for partner in deceased if partner.death]
        if deceased:
            is_over = True
            # An unknown death date may be the earliest one, so it wins.
            if len(death_years) == len(deceased):
                end_year = min(death_years)

    if start_year and end_year:
        return f"{start_year}–{end_year}"
    if start_year and is_over:
        return f"{start_year}–?"
    if start_year:
        return _("since %(year)s") % {"year": start_year}
    if end_year:
        return _("until %(year)s") % {"year": end_year}
    return ""


def build_person_page(person: Person) -> dict:
    """The values used by the template family/person_detail.html."""
    graph = load_family_graph()
    me = person.identifier
    targets = LinkTargets.from_database()

    parents = graph.parents(me)
    siblings = graph.siblings(me)
    grandchildren = graph.grandchildren(me)
    union_records = graph.unions_of(me)

    needed = {relative.person for relative in parents}
    needed |= set(siblings.all) | set(grandchildren)
    needed |= {child for record in union_records for child, _kind in record.children}
    people = {
        relative.identifier: relative
        for relative in Person.objects.filter(identifier__in=needed)
    }

    stored_unions = {
        union.pk: union
        for union in Union.objects.filter(
            pk__in=[record.id for record in union_records]
        ).select_related("partner1", "partner2")
    }
    unions = []
    for record in union_records:
        union = stored_unions[record.id]
        unions.append(
            UnionView(
                partner=union.partner_of(person),
                kind=union.get_kind_display(),
                period=union_period(union),
                is_ended=union.is_ended,
                children=[
                    RelativeView(people[child], link_note(kind))
                    for child, kind in record.children
                ],
                story=render_text(union.story, targets).html,
            )
        )

    sections = []
    for key, title in TEXT_SECTIONS:
        html = render_text(getattr(person, key), targets, video_id=person.youtube_id).html
        stories = [union for union in unions if union.story] if key == "love" else []
        if html or stories:
            sections.append(SectionView(key, title, html, stories))

    video_id = person.youtube_id
    return {
        "person": person,
        "parents": [
            RelativeView(people[relative.person], link_note(relative.kind))
            for relative in parents
        ],
        "full_siblings": [people[identifier] for identifier in siblings.full],
        "half_siblings": [people[identifier] for identifier in siblings.half],
        "step_siblings": [people[identifier] for identifier in siblings.step],
        "unions": unions,
        "grandchildren": [people[identifier] for identifier in grandchildren],
        "sections": sections,
        "interview_embed_url": embed_url(video_id) if video_id else "",
        "interview_watch_url": watch_url(video_id) if video_id else "",
        "lived_in": list(person.lived_in.all()),
    }
