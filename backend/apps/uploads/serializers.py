from rest_framework import serializers
from apps.uploads.models import Upload


class UploadSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Upload
        fields = [
            'id',
            'original_name',
            'mime_type',
            'size_bytes',
            'kind',
            'file_url',
            'analysis_status',
            'analysis_result',
            'created_at',
        ]

    def get_file_url(self, obj: Upload) -> str:
        return obj.file.url if obj.file else ""


class UploadCreateSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)
