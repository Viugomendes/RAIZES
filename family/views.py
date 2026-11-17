"""The pages: each function gathers the data and fills a template."""
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, render

from .images import VariantError, make_variant, parse_variant_path
from .markup import LinkTargets, render_text
from .models import Person, Photo, Recipe
from .person_page import build_person_page
from .site_data import site_data_script
from .strings import map_strings, mural_strings, search_strings, tree_strings
from .tree_page import build_tree_page


def home(request):
    """1 · News: the automatic mural, calculated in the browser every day."""
    return render(
        request,
        "family/home.html",
        {
            "nav": "home",
            "strings": mural_strings(),
            "has_people": Person.objects.exists(),
            "who_count": Photo.objects.filter(has_unidentified_people=True).count(),
        },
    )


def tree(request):
    context = build_tree_page()
    context["nav"] = "tree"
    context["mode"] = "tree"
    context["strings"] = tree_strings()
    return render(request, "family/tree.html", context)


def family_map(request):
    return render(
        request,
        "family/map.html",
        {"nav": "tree", "mode": "map", "strings": map_strings()},
    )


def search(request):
    return render(request, "family/search.html", {"nav": "search", "strings": search_strings()})


def person_detail(request, identifier):
    person = get_object_or_404(
        Person.objects.select_related("birth_place", "death_place", "resting_place", "lives_in"),
        identifier=identifier,
    )
    context = build_person_page(person)
    return render(request, "family/person_detail.html", context)


def recipe_detail(request, slug):
    recipe = get_object_or_404(Recipe.objects.select_related("author"), slug=slug)
    text = render_text(recipe.text, LinkTargets.from_database()).html
    return render(request, "family/recipe_detail.html", {"recipe": recipe, "text": text})


def who_is_this(request):
    photos = Photo.objects.filter(has_unidentified_people=True).prefetch_related("people")
    return render(request, "family/who.html", {"photos": photos})


def family_data(request):
    return HttpResponse(site_data_script(), content_type="text/javascript; charset=utf-8")


def media_variant(request, path):
    """A smaller copy of a photo, made on request (only while working locally)."""
    parsed = parse_variant_path(path)
    if parsed is None:
        raise Http404
    try:
        file = make_variant(parsed[1], parsed[0])
    except VariantError:
        raise Http404 from None
    return FileResponse(open(file, "rb"), content_type="image/jpeg")
