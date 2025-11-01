from django.urls import path, include
from .views import auth_views

app_name = "internal_api"

urlpatterns = [
    # Authentication endpoints
    path("auth/register/", auth_views.register, name="register"),  # User registration
    path("auth/login/", auth_views.login_view, name="login"),  # User login
    path("auth/logout/", auth_views.logout_view, name="logout"),  # User logout
    path("auth/csrf/", auth_views.get_csrf_token, name="csrf-token"),  # Get CSRF token
    path("auth/me/", auth_views.user_info, name="user-info"),  # Get current user info
    path("auth/profile/", auth_views.update_profile, name="update-profile"),  # User profile
    path("auth/change-password/", auth_views.change_password, name="change-password"),  # Password management
    path("auth/delete-account/", auth_views.delete_account, name="delete-account"),  # Account deletion
]
