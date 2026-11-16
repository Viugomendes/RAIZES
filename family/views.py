"""The pages: each function gathers the data and fills a template."""
from django.shortcuts import get_object_or_404, render

from .models import Person
from .person_page import build_person_page


def tree(request):
    return render(request, "family/tree.html", {"nav": "tree"})


def person_list(request):
    people = Person.objects.all()
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
