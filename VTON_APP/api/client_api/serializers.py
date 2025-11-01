from rest_framework import serializers
from app.models.vton_models import VTONRequest
from app.Controllers.HelpersController import VTONRequestHelper


class VTONSerializer(serializers.Serializer):
    """Serializer for VTON request input validation."""

    person_image = serializers.FileField()
    clothing_image = serializers.FileField()
    instructions = serializers.CharField(max_length=500, required=False, allow_blank=True)


class VTONResponseSerializer(serializers.ModelSerializer):
    """
    Serializer for VTON request response with public URLs and comprehensive metadata.
    """

    person_image_url = serializers.SerializerMethodField()
    clothing_image_url = serializers.SerializerMethodField()
    result_image_url = serializers.SerializerMethodField()
    processing_duration_seconds = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = VTONRequest
        fields = [
            "request_id",
            "person_image_url",
            "clothing_image_url",
            "result_image_url",
            "status",
            "error_message",
            "person_image_size",
            "clothing_image_size",
            "result_image_size",
            "processing_duration_seconds",
            "created_at",
            "updated_at",
            "completed_at",
            "processing_started_at",
            "processing_completed_at",
            "source",
            "metadata",
        ]

    def get_person_image_url(self, obj):
        request = self.context.get("request")
        return VTONRequestHelper.get_person_image_url(obj, request)

    def get_clothing_image_url(self, obj):
        request = self.context.get("request")
        return VTONRequestHelper.get_clothing_image_url(obj, request)

    def get_result_image_url(self, obj):
        request = self.context.get("request")
        return VTONRequestHelper.get_result_image_url(obj, request)
