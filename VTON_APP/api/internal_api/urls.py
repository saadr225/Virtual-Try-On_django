from django.urls import path
from .views import auth_views, client_api_management_views, admin_views, docs_view

app_name = "internal_api"

urlpatterns = [
    # Authentication endpoints (JWT-based)
    path("auth/register/", auth_views.register, name="register"),  # User registration
    path("auth/login/", auth_views.login_view, name="login"),  # User login (returns JWT tokens)
    path("auth/admin-login/", auth_views.admin_login_view, name="admin-login"),  # Admin-only login (rejects non-admin users)
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
    # User Quota endpoints (JWT authentication required)
    path("quota/me/", client_api_management_views.get_my_quota, name="get-my-quota"),  # Get current user's quota info
    # Admin endpoints (Admin only - JWT authentication + admin permission required)
    path("admin/users/quotas/", admin_views.list_all_users_quotas, name="admin-list-user-quotas"),  # List all users with quotas
    path("admin/users/search/", admin_views.search_users, name="admin-search-users"),  # Search for users
    path("admin/users/<str:username>/quota/", admin_views.get_user_quota, name="admin-get-user-quota"),  # Get specific user quota
    path("admin/users/<str:username>/quota/update/", admin_views.update_user_quota, name="admin-update-user-quota"),  # Update user quota
    path("admin/users/<str:username>/details/", admin_views.get_user_details, name="admin-get-user-details"),  # Get comprehensive user details
    path("admin/api-keys/", admin_views.list_all_api_keys, name="admin-list-all-api-keys"),  # List all API keys (all users)
    path("admin/api-keys/<uuid:key_id>/update/", admin_views.admin_update_api_key, name="admin-update-api-key"),  # Admin update any API key
    path("admin/api-keys/<uuid:key_id>/delete/", admin_views.admin_delete_api_key, name="admin-delete-api-key"),  # Admin delete any API key
    # API Documentation endpoints
    path("docs/", docs_view.api_docs_info, name="api-docs-info"),  # Get information about available API documentation
    path("docs/client-api-spec/", docs_view.client_api_spec, name="client-api-spec"),  # Public: Client API OpenAPI spec
    path("docs/internal-api-spec/", docs_view.internal_api_spec, name="internal-api-spec"),  # Admin only: Internal API OpenAPI spec
]
