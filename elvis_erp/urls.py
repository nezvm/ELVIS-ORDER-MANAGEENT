from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from registration.backends.default import urls as registration_urls

urlpatterns = [
    path("", include("core.urls")),
    path("master/", include("master.urls")),
    path("accounts/", include("accounts.urls")),
    path("admin/", admin.site.urls),
    path("accounts/", include(registration_urls)),
    path("tinymce/", include("tinymce.urls")),
    
    # New module URLs
    path("channels/", include("channels_config.urls")),
    path("logistics/", include("logistics.urls")),
    path("inventory/", include("inventory.urls")),
    path("segmentation/", include("segmentation.urls")),
    path("integrations/", include("integrations.urls")),
    path("marketing/", include("marketing.urls")),
    
    # REST API
    path("api/v1/", include("api.urls")),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_FILE_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
