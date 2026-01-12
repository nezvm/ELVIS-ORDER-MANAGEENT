from django.urls import path
from . import views

app_name = 'segmentation'

urlpatterns = [
    # Dashboard
    path('', views.SegmentationDashboardView.as_view(), name='dashboard'),
    
    # Customer Profiles
    path('profiles/', views.CustomerProfileListView.as_view(), name='profile_list'),
    path('profile/<uuid:pk>/', views.CustomerProfileDetailView.as_view(), name='profile_detail'),
    
    # Segments
    path('segments/', views.CustomerSegmentListView.as_view(), name='segment_list'),
    path('segment/<uuid:pk>/', views.CustomerSegmentDetailView.as_view(), name='segment_detail'),
    path('segment/new/', views.CustomerSegmentCreateView.as_view(), name='segment_create'),
    path('segment/<uuid:pk>/update/', views.CustomerSegmentUpdateView.as_view(), name='segment_update'),
    path('segment/<uuid:pk>/delete/', views.CustomerSegmentDeleteView.as_view(), name='segment_delete'),
    
    # Cohort Analysis
    path('cohorts/', views.CohortAnalysisView.as_view(), name='cohort_analysis'),
    
    # API Endpoints
    path('api/compute-profiles/', views.compute_profiles, name='compute_profiles'),
    path('api/segment/<uuid:pk>/refresh/', views.refresh_segment, name='refresh_segment'),
    path('api/segment/<uuid:pk>/export/', views.export_segment, name='export_segment'),
    path('api/compute-cohorts/', views.compute_cohorts, name='compute_cohorts'),
    path('api/dashboard-data/', views.segmentation_dashboard_data, name='dashboard_data'),
]
