from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy

from core import mixins

from . import tables
from .models import User


class UserListView(mixins.HybridListView):
    model = User
    table_class = tables.UserTable
    template_name = 'user/list.html'
    filterset_fields = ("is_active", "is_staff", "usertype")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Users"
        context["is_master"] = True
        context["is_user"] = True
        context["can_add"] = True
        context["new_link"] = reverse_lazy("accounts:user_create")
        return context


class UserDetailView(mixins.HybridDetailView):
    model = User
    permissions = ("Superadmin", "Admin", "Staff",)
    template_name = "user/detail.html"


class UserCreateView(mixins.HybridCreateView):
    model = User
    fields = ('first_name','code','email', "usertype","username", "password",)
    permissions = ("Superadmin", "Admin",)
    template_name = 'user/form.html'

   

    def form_valid(self, form):
        form.instance.set_password(form.cleaned_data["password"])
        form.instance.password2 =form.cleaned_data["password"]
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Employee'
        context['subtitle'] = 'Account Details'
        context['is_account'] = True
        return context

    def get_success_url(self):
        return reverse_lazy("accounts:user_list")

    def get_success_message(self, cleaned_data):
        message = "Employee created successfully"
        return message


class UserUpdateView(mixins.HybridUpdateView):
    model = User
    fields = ("username",'first_name','code','email',"usertype")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Employee'
        context['subtitle'] = 'Account Details'
        context['is_account'] = True
        return context

    def get_success_url(self):
        return reverse_lazy("accounts:user_list")

    def get_success_message(self, cleaned_data):
        message = "Employee Updated successfully"
        return message

    
class UserDeleteView(mixins.HybridDeleteView):
    model = User
    permissions = ("Superadmin",)
