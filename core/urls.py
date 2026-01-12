from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("report/", views.ReportView.as_view(), name="report"),
    path("channel_report/", views.ChannelReportView.as_view(), name="channel_report"),
]
