from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "core"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("report/", views.ReportView.as_view(), name="report"),
    path("channel_report/", views.ChannelReportView.as_view(), name="channel_report"),
    
    # Legal pages (public - no login required)
    path("privacy-policy/", TemplateView.as_view(template_name="legal/privacy_policy.html"), name="privacy_policy"),
    path("terms-of-service/", TemplateView.as_view(template_name="legal/terms_of_service.html"), name="terms_of_service"),
    path("data-deletion/", TemplateView.as_view(template_name="legal/data_deletion.html"), name="data_deletion"),
]
