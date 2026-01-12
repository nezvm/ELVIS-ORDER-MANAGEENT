from django.urls import path
from . import views

app_name = 'channels_config'

urlpatterns = [
    # Channel management
    path('channels/', views.ChannelListView.as_view(), name='channel_list'),
    path('channel/<uuid:pk>/', views.ChannelDetailView.as_view(), name='channel_detail'),
    path('channel/new/', views.ChannelCreateView.as_view(), name='channel_create'),
    path('channel/<uuid:pk>/update/', views.ChannelUpdateView.as_view(), name='channel_update'),
    path('channel/<uuid:pk>/delete/', views.ChannelDeleteView.as_view(), name='channel_delete'),
    
    # Form field management
    path('form-fields/', views.FormFieldListView.as_view(), name='formfield_list'),
    path('form-field/new/', views.FormFieldCreateView.as_view(), name='formfield_create'),
    path('form-field/<uuid:pk>/update/', views.FormFieldUpdateView.as_view(), name='formfield_update'),
    path('form-field/<uuid:pk>/delete/', views.FormFieldDeleteView.as_view(), name='formfield_delete'),
    
    # API endpoints
    path('api/validate-utr/', views.validate_utr, name='validate_utr'),
    path('api/channel-fields/', views.get_channel_fields, name='channel_fields'),
]
