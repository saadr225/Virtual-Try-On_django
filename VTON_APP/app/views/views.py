from django.shortcuts import render
from django.http import JsonResponse

# Create your views here.


def homepage(request):
    """
    Simple homepage view for health checks
    """
    return JsonResponse({"status": "ok", "message": "VTON Application is running", "service": "VTON API"})
