from rest_framework import serializers


class VTONSerializer(serializers.Serializer):
    person_image = serializers.FileField()
    clothing_image = serializers.FileField()
    instructions = serializers.CharField(max_length=500, required=False, allow_blank=True)
