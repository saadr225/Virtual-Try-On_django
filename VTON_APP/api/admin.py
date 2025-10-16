from django.contrib import admin
from .models import VTONRequest


# Register your models here.
@admin.register(VTONRequest)
class VTONRequestAdmin(admin.ModelAdmin):
    list_display = ["request_id", "status", "person_image_original_name", "clothing_image_original_name", "created_at", "completed_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["request_id", "person_image_original_name", "clothing_image_original_name"]
    readonly_fields = ["request_id", "created_at", "updated_at", "completed_at", "person_image_original_name", "clothing_image_original_name"]
    ordering = ["-created_at"]

    fieldsets = (
        ("Request Information", {"fields": ("request_id", "status", "instructions")}),
        ("Uploaded Images", {"fields": ("person_image", "person_image_original_name", "clothing_image", "clothing_image_original_name")}),
        ("Result", {"fields": ("result_image", "error_message")}),
        ("Timestamps", {"fields": ("created_at", "updated_at", "completed_at")}),
    )
