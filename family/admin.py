"""The admin panel: the forms where the owner fills in the family.

Registered on the panel at /painel/ (access/admin_site.py); never exported with the site.
"""
from django.conf import settings
from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _

from access.admin_site import site

from .markup import LinkTargets
from .models import TEXT_SECTIONS, ChildLink, Clip, Person, Photo, Place, Recipe, Union
from .textcheck import person_problems, union_problems

# The header always says which family is loaded, so that real data is never
# typed into the invented family by mistake (or the other way round).
if settings.RAIZES_DATASET == "demo":
    site.site_header = _("Raízes · invented family (demo)")
else:
    site.site_header = _("Raízes · REAL family data")
site.site_title = "Raízes"
site.index_title = _("Family data")


def warn_about_text_problems(request, problems: list[str]) -> None:
    """Show a warning for each link in a text that points nowhere.

    The record is saved anyway: it is normal to mention someone who will only
    be added later. The export, however, refuses to run while problems remain.
    """
    for problem in problems:
        messages.warning(request, problem)


@admin.register(Place, site=site)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "latitude", "longitude")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Person, site=site)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("full_name", "identifier", "years_display", "deceased", "confirmed")
    list_filter = ("confirmed", "deceased", "sex")
    search_fields = ("given_name", "surname", "nickname", "other_names", "identifier")
    autocomplete_fields = (
        "birth_place",
        "death_place",
        "resting_place",
        "lives_in",
        "lived_in",
    )
    fieldsets = (
        (
            _("Who"),
            {"fields": ("given_name", "surname", "nickname", "other_names", "sex", "identifier")},
        ),
        (_("Birth"), {"fields": ("birth_date", "birth_date_approximate", "birth_place")}),
        (
            _("Death"),
            {
                "fields": (
                    "deceased",
                    "death_date",
                    "death_date_approximate",
                    "death_place",
                    "resting_place",
                )
            },
        ),
        (_("Life"), {"fields": ("lives_in", "lived_in", "occupation", "tags")}),
        (_("Photo and interview"), {"fields": ("photo", "interview_url")}),
        (_("Reliability"), {"fields": ("confirmed", "source")}),
        (
            _("Texts of the page (all optional)"),
            {"fields": tuple(name for name, _title in TEXT_SECTIONS)},
        ),
    )

    @admin.display(description=_("name"), ordering="given_name")
    def full_name(self, person):
        return person.full_name

    @admin.display(description=_("years"))
    def years_display(self, person):
        return person.years_display

    def get_readonly_fields(self, request, obj=None):
        # The identifier can be typed when creating a person, never afterwards.
        return ("identifier",) if obj else ()

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        warn_about_text_problems(request, person_problems(obj, LinkTargets.from_database()))


class ChildLinkInline(admin.TabularInline):
    model = ChildLink
    extra = 1
    autocomplete_fields = ("child",)


@admin.register(Union, site=site)
class UnionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "kind", "start_date", "end_date", "ended")
    list_filter = ("kind", "ended")
    search_fields = (
        "partner1__given_name",
        "partner1__surname",
        "partner2__given_name",
        "partner2__surname",
    )
    autocomplete_fields = ("partner1", "partner2")
    fields = ("partner1", "partner2", "kind", "start_date", "end_date", "ended", "story")
    inlines = (ChildLinkInline,)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        warn_about_text_problems(request, union_problems(obj, LinkTargets.from_database()))


@admin.register(Photo, site=site)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ("__str__", "date", "place", "has_unidentified_people")
    list_filter = ("has_unidentified_people",)
    search_fields = ("caption", "people__given_name", "people__surname")
    autocomplete_fields = ("place", "people")
    fields = ("image", "date", "place", "caption", "people", "has_unidentified_people")


@admin.register(Clip, site=site)
class ClipAdmin(admin.ModelAdmin):
    list_display = ("__str__", "date")
    search_fields = ("caption", "people__given_name", "people__surname")
    autocomplete_fields = ("people",)
    fields = ("file", "caption", "date", "people")


@admin.register(Recipe, site=site)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("title", "author")
    search_fields = ("title",)
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("author",)
