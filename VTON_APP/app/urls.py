from django.urls import path
from app.views.views import homepage

# from rest_framework_simplejwt.views import TokenRefreshView
urlpatterns = [
    path("", homepage, name="homepage"),
]
