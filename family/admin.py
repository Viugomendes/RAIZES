"""The admin panel: the forms where the owner fills in the family.

It runs only on the owner's computer and is never exported with the site.
"""
from django.conf import settings
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import TEXT_SECTIONS, ChildLink, Person, Photo, Place, Recipe, Union

# The header always says which family is loaded, so that real data is never
# typed into the invented family by mistake (or the other way round).
if settings.RAIZES_DATASET == "demo":
    admin.site.site_header = _("Raízes · invented family (demo)")
else:
    admin.site.site_header = _("Raízes · REAL family data")
admin.site.site_title = "Raízes"
admin.site.index_title = _("Family data")


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "latitude", "longitude")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Person)
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


class ChildLinkInline(admin.TabularInline):
    model = ChildLink
    extra = 1
    autocomplete_fields = ("child",)


@admin.register(Union)
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


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ("__str__", "year", "place")
    search_fields = ("caption",)
    autocomplete_fields = ("place", "people")


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("title", "author")
    search_fields = ("title",)
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("author",)
