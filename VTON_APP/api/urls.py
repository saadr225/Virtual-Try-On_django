from django.urls import path
from .views import (
    semantic_views,
)

# from rest_framework_simplejwt.views import TokenRefreshView
urlpatterns = [
    # virtual tryon views
    path("virtual-tryon/", semantic_views.virtual_tryon, name="virtual-tryon")
]
