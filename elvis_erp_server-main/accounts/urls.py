from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("users/", views.UserListView.as_view(), name="user_list"),
    path("user/<str:pk>/", views.UserDetailView.as_view(), name="user_detail"),
    path("new/user/", views.UserCreateView.as_view(), name="user_create"),
    path("new/user/<str:pk>/", views.UserCreateView.as_view(), name="user_create"),
    path("user/<str:pk>/update/", views.UserUpdateView.as_view(), name="user_update"),
    path("user/<str:pk>/delete/", views.UserDeleteView.as_view(), name="user_delete"),
]
