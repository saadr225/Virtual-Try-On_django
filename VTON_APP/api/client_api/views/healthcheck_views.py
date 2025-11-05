from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
import psutil
import datetime


@api_view(["GET"])
@permission_classes([AllowAny])
@csrf_exempt
def healthcheck(request):
    # Basic health info
    uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())
    cpu_usage = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()

    return Response(
        {
            "status": "healthy",
            "timestamp": datetime.datetime.now().isoformat(),
            "uptime": str(uptime),
            "cpu_usage_percent": cpu_usage,
            "memory_usage_percent": memory.percent,
            "total_memory_gb": round(memory.total / (1024**3), 2),
            "available_memory_gb": round(memory.available / (1024**3), 2),
        },
        status=status.HTTP_200_OK,
    )
