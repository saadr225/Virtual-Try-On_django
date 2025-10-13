import secrets
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from app.models import UserData
from django.utils import timezone


class MediaUpload(models.Model):
    user = models.ForeignKey(UserData, on_delete=models.CASCADE)
    # file = models.FileField(upload_to=f"{settings.MEDIA_ROOT}/submissions", max_length=512)
    file = models.FileField(upload_to=f"submissions/", max_length=512)
    original_filename = models.CharField(max_length=256, blank=False)
    submission_identifier = models.CharField(max_length=128, blank=False)
    file_identifier = models.CharField(max_length=128, blank=False)
    file_type = models.CharField(max_length=32, default="Video")
    purpose = models.CharField(max_length=32, default="Deepfake-Analaysis", blank=False)
    upload_date = models.DateTimeField(auto_now_add=True)
    # description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.file.name} - {self.upload_date}"
