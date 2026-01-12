from django.contrib import admin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.core.exceptions import ValidationError
from import_export.admin import ExportActionModelAdmin, ImportExportMixin

from .models import User


class MyUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User


class MyUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User

    def clean_username(self):
        username = self.cleaned_data["username"]
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return username
        raise ValidationError("Username already exists")


class MyUserAdmin(ImportExportMixin, ExportActionModelAdmin):
    form = MyUserChangeForm
    add_form = MyUserCreationForm
    ordering = ("username",)
    list_display = ("username", "usertype", "is_active", "last_login", "date_joined", "is_staff", "is_superuser")
    list_display_links = ("username",)
    readonly_fields = ("last_login", "date_joined", "pk")
    list_filter = ("is_active", "is_staff", "is_superuser", "date_joined", "last_login", "usertype")
    fieldsets = (
        ("Basic Info", {"fields": ("username", "password", "email", "usertype")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Groups", {"fields": ("groups",)}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    search_fields = ("username", "email")


admin.site.register(User, MyUserAdmin)
