import operator
import re
from functools import reduce

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import FieldError
from django.db.models import Q
from django.forms import models as model_forms
from django.views.generic import DetailView, View
from django.views.generic.base import TemplateView
from django.views.generic.edit import CreateView, DeleteView, FormView, UpdateView
from django.views.generic.list import ListView
from django_filters.views import FilterView
from django_tables2.export.views import ExportMixin
from django_tables2.views import SingleTableMixin


def convert_to_spaces(text):
    result = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    return result


def check_access(request, permissions):
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.usertype in permissions:
            return True
    return False


class CustomLoginRequiredMixin(LoginRequiredMixin):
    permissions = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if self.permissions and not check_access(request, self.permissions):
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)


class CustomModelFormMixin:
    exclude = None

    # Rewriting get_form_class to support exclude attribute
    def get_form_class(self):
        model = getattr(self, "model", None)
        if self.exclude:
            exclude = getattr(self, "exclude", None)
            return model_forms.modelform_factory(model, exclude=exclude)
        return super().get_form_class()


class HybridDetailView(CustomLoginRequiredMixin, DetailView):
    template_name = "app/common/object_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # extra_context = getattr(self, "extra_context", {})
        # context.update(extra_context)
        if "title" not in context:
            context["title"] = self.get_object().__str__
        return context


class HybridCreateView(CustomLoginRequiredMixin, CustomModelFormMixin, SuccessMessageMixin, CreateView):
    template_name = "app/common/object_form.html"

    def get_success_url(self):
        return self.object.get_list_url()

    def form_valid(self, form):
        form.instance.creator = self.request.user
        response = super().form_valid(form)
        return response

    def get_success_message(self, cleaned_data):
        instance = self.object
        success_message = f"{self.model.__name__} '{instance}' was Created successfully. "
        success_message += f"<a href='{instance.get_absolute_url()}'>View {self.model.__name__}</a>."
        return success_message

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "New " + convert_to_spaces(self.model.__name__)
        return context


class HybridUpdateView(CustomLoginRequiredMixin, CustomModelFormMixin, SuccessMessageMixin, UpdateView):
    template_name = "app/common/object_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        return response

    def get_success_message(self, cleaned_data):
        instance = self.object
        success_message = f"{self.model.__name__} '{instance}' was Updated successfully. "
        success_message += f"<a href='{instance.get_absolute_url()}'>View {self.model.__name__}</a>."
        return success_message

    def get_success_url(self):
        return self.object.get_list_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Update " + convert_to_spaces(self.model.__name__)
        return context


class HybridDeleteView(CustomLoginRequiredMixin, DeleteView):
    template_name = "app/common/confirm_delete.html"

    def get_success_url(self):
        return self.object.get_list_url()


class HybridListView(CustomLoginRequiredMixin, ExportMixin, SingleTableMixin, FilterView, ListView):
    template_name = "app/common/object_list.html"
    table_pagination = {"per_page": 500}

    def get_queryset(self):
        queryset = super().get_queryset()
        search_fields = getattr(self, "search_fields", None)
        if search_fields:
            query = self.request.GET.get("q")
            if query:
                q_list = [Q(**{f"{field}__icontains": query}) for field in search_fields]
                queryset = queryset.filter(reduce(operator.or_, q_list))
        try:
            queryset.filter(is_active=True)
            return queryset.filter(is_active=True)
        except FieldError:
            return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.model._meta.verbose_name_plural
        context["can_add"] = False
        context["new_link"] = self.model.get_create_url() if hasattr(self.model, "get_create_url") else None
        return context


class HybridFormView(CustomLoginRequiredMixin, FormView):
    pass


class HybridTemplateView(CustomLoginRequiredMixin, TemplateView):
    template_name = "app/common/object_view.html"


class HybridView(CustomLoginRequiredMixin, View):
    pass


class OpenView(TemplateView):
    pass
