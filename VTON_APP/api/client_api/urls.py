from django.urls import path
from api.client_api.views import semantic_views

app_name = "client_api"

# from rest_framework_simplejwt.views import TokenRefreshView
urlpatterns = [
    # virtual tryon views
    path("virtual-tryon/process/", semantic_views.virtual_tryon, name="virtual-tryon"),  # Process try-on request
    path("virtual-tryon/<uuid:request_id>/status/", semantic_views.get_request_status, name="vton-request-status"),  # Get status of a specific request
    path("virtual-tryon/requests/", semantic_views.list_recent_requests, name="vton-list-requests"),  # List recent requests
]
