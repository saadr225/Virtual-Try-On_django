from rest_framework import serializers
from api.internal_api.models import VTONRequest
from app.Controllers.HelpersController import VTONRequestHelper


class VTONSerializer(serializers.Serializer):
    person_image = serializers.FileField()
    clothing_image = serializers.FileField()
    instructions = serializers.CharField(max_length=500, required=False, allow_blank=True)
    # DEPRECATED: cloths_on is no longer used by Vertex AI Virtual Try-On API
    # Kept for backward compatibility with existing API clients
    cloths_on = serializers.BooleanField(
        required=False, default=False, help_text="DEPRECATED: This field is no longer used. Vertex AI automatically handles both scenarios."
    )


class VTONResponseSerializer(serializers.ModelSerializer):
    """
    Serializer for VTON request response with public URLs
    """

    person_image_url = serializers.SerializerMethodField()
    clothing_image_url = serializers.SerializerMethodField()
    result_image_url = serializers.SerializerMethodField()

    class Meta:
        model = VTONRequest
        fields = [
            "request_id",
            "person_image_url",
            "clothing_image_url",
            "result_image_url",
            "instructions",
            "cloths_on",
            "status",
            "error_message",
            "created_at",
            "updated_at",
            "completed_at",
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
