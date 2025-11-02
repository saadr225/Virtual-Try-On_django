from django.urls import path
from .views import auth_views, client_api_management_views

app_name = "internal_api"

urlpatterns = [
    # Authentication endpoints (JWT-based)
    path("auth/register/", auth_views.register, name="register"),  # User registration
    path("auth/login/", auth_views.login_view, name="login"),  # User login (returns JWT tokens)
    path("auth/logout/", auth_views.logout_view, name="logout"),  # User logout (blacklists JWT refresh token)
    path("auth/token/refresh/", auth_views.token_refresh_view, name="token-refresh"),  # JWT token refresh
    # User Profile endpoints (JWT authentication required)
    path("auth/me/", auth_views.user_info, name="user-info"),  # Get current user info
    path("auth/profile/", auth_views.update_profile, name="update-profile"),  # Update user profile
    path("auth/change-password/", auth_views.change_password, name="change-password"),  # Change password
    path("auth/delete-account/", auth_views.delete_account, name="delete-account"),  # Delete account
    # API Key Management endpoints (JWT authentication required)
    path("api-keys/", client_api_management_views.list_api_keys, name="list-api-keys"),  # List all API keys
    path("api-keys/create/", client_api_management_views.create_api_key, name="create-api-key"),  # Create new API key
    path("api-keys/<uuid:key_id>/", client_api_management_views.get_api_key_detail, name="get-api-key"),  # Get API key details
    path("api-keys/<uuid:key_id>/update/", client_api_management_views.update_api_key, name="update-api-key"),  # Update API key
    path("api-keys/<uuid:key_id>/delete/", client_api_management_views.delete_api_key, name="delete-api-key"),  # Delete API key
    path("api-keys/<uuid:key_id>/regenerate/", client_api_management_views.regenerate_api_key, name="regenerate-api-key"),  # Regenerate API key
    path("api-keys/<uuid:key_id>/stats/", client_api_management_views.get_api_key_stats, name="api-key-stats"),  # Get API key stats
]
