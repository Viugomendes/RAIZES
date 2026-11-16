"""The pages: each function gathers the data and fills a template."""
import unicodedata

from django.shortcuts import get_object_or_404, render

from .models import Person
from .person_page import build_person_page
from .tree_page import build_tree_page


def tree(request):
    context = build_tree_page()
    context["nav"] = "tree"
    return render(request, "family/tree.html", context)


def _alphabetical(person: Person) -> str:
    """Sort key that ignores accents and capitals: "Álvaro" goes with the As."""
    decomposed = unicodedata.normalize("NFKD", person.full_name)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()


def person_list(request):
    people = sorted(Person.objects.all(), key=_alphabetical)
    return render(request, "family/person_list.html", {"nav": "people", "people": people})


def person_detail(request, identifier):
    person = get_object_or_404(
        Person.objects.select_related(
            "birth_place", "death_place", "resting_place", "lives_in"
        ),
        identifier=identifier,
    )
    context = build_person_page(person)
    context["nav"] = "people"
    return render(request, "family/person_detail.html", context)
