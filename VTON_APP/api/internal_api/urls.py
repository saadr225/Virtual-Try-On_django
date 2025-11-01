from django.urls import path
from .views import auth_views

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
]
