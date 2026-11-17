"""Panel pages: site settings (one row) and the connected devices."""
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .admin_site import site
from .forms import SiteSettingsForm
from .models import SiteSettings, ViewerDevice


@admin.register(SiteSettings, site=site)
class SiteSettingsAdmin(admin.ModelAdmin):
    form = SiteSettingsForm
    autocomplete_fields = ("central_person",)
    fieldsets = (
        (None, {"fields": ("family_name", "central_person")}),
        (
            _("Family password"),
            {
                "fields": ("new_view_password", "repeat_view_password"),
                "description": _(
                    "Saving a new password disconnects every device. "
                    "The site language is chosen in the installer (the .env file) and is not changed here."
                ),
            },
        ),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # One row only: the list is the edit page.
        row = SiteSettings.get()
        return HttpResponseRedirect(reverse("admin:access_sitesettings_change", args=[row.pk]))

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        new = form.cleaned_data.get("new_view_password")
        if new:
            obj.set_view_password(new)
            messages.success(
                request, _("The new password was saved. All devices were disconnected.")
            )


class OnlineFilter(admin.SimpleListFilter):
    title = _("online now")
    parameter_name = "online"

    def lookups(self, request, model_admin):
        return [("yes", _("Online now"))]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            from .models import ONLINE_WINDOW

            return queryset.filter(last_seen__gte=timezone.now() - ONLINE_WINDOW)
        return queryset


@admin.register(ViewerDevice, site=site)
class ViewerDeviceAdmin(admin.ModelAdmin):
    list_display = ("status", "name", "browser", "ip_prefix", "entered", "last_visit")
    list_display_links = ("name",)
    list_filter = (OnlineFilter,)
    actions = ["disconnect"]
    ordering = ("-last_seen",)
    list_per_page = 50

    class Media:
        css = {"all": ("access/panel.css",)}

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_disconnect_permission(self, request):
        return request.user.has_perm("access.change_viewerdevice")

    @admin.display(description=_("Status"))
    def status(self, obj):
        if obj.revoked or not obj.is_valid(SiteSettings.get()):
            return format_html('<span class="raizes-status raizes-off">{}</span>', _("Disconnected"))
        if obj.is_online:
            return format_html('<span class="raizes-status raizes-on">{}</span>', _("Online"))
        return format_html('<span class="raizes-status">{}</span>', _("Offline"))

    @admin.display(description=_("Entered"), ordering="created_at")
    def entered(self, obj):
        return timezone.localtime(obj.created_at).strftime("%d/%m/%Y %H:%M")

    @admin.display(description=_("Last visit"), ordering="last_seen")
    def last_visit(self, obj):
        return timezone.localtime(obj.last_seen).strftime("%d/%m/%Y %H:%M")

    @admin.action(description=_("Disconnect the selected devices"), permissions=["disconnect"])
    def disconnect(self, request, queryset):
        count = queryset.update(revoked=True)
        self.message_user(request, _("Devices disconnected: %(count)d.") % {"count": count}, messages.SUCCESS)
