from django.db import models
from django.http import HttpResponseRedirect
from django_tables2 import Table, columns
from import_export.admin import ImportExportModelAdmin

from core.actions import mark_active, mark_inactive
from core.choices import BOOL_CHOICES

from .functions import generate_fields


class BaseModel(models.Model):
    created = models.DateTimeField(db_index=True, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    creator = models.ForeignKey("accounts.User", editable=False, blank=True, null=True, related_name="%(app_label)s_%(class)s_creator", on_delete=models.SET_NULL)
    is_active = models.BooleanField("Mark as Active", default=True, choices=BOOL_CHOICES)

    class Meta:
        abstract = True
        ordering = ["-created"]

    def get_fields(self):
        return generate_fields(self)

    def delete(self, *args, **kwargs):
        self.is_active = False
        self.save()
        return HttpResponseRedirect(self.get_list_url())


class BaseAdmin(ImportExportModelAdmin):
    exclude = ["creator"]
    list_display = ("__str__", "created", "updated", "is_active")
    list_filter = ("is_active",)
    actions = [mark_active, mark_inactive]
    readonly_fields = ("creator", "pk")
    search_fields = ("pk",)

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        context.update({"show_save_and_continue": False, "show_save_and_add_another": True})
        return super().render_change_form(request, context, add, change, form_url, obj)

    def save_model(self, request, obj, form, change):
        if not obj.creator:
            obj.creator = request.user
        super().save_model(request, obj, form, change)

    class Media:
        css = {"all": ("extra_admin/css/admin.css",)}


class BaseTable(Table):
    # pk = columns.Column(visible=False)
    created = columns.DateTimeColumn(verbose_name="Created At", format="d/m/Y g:i A")
    action = columns.TemplateColumn(template_name="app/partials/table_actions_normal.html", orderable=False)
