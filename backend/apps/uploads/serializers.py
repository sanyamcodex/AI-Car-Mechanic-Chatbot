from rest_framework import serializers
from apps.uploads.models import Upload


class UploadSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    conversation_id = serializers.UUIDField(read_only=True)
    mime = serializers.CharField(source='mime_type', read_only=True)
    size = serializers.IntegerField(source='size_bytes', read_only=True)
    status = serializers.CharField(source='analysis_status', read_only=True)

    class Meta:
        model = Upload
        fields = [
            'id',
            'conversation_id',
            'original_name',
            'mime',
            'mime_type',
            'size',
            'size_bytes',
            'kind',
            'url',
            'file_url',
            'analysis_status',
            'status',
            'analysis_result',
            'created_at',
        ]

    def _absolute_url(self, obj: Upload) -> str:
        request = self.context.get('request')
        if obj.file:
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return ""

    def get_url(self, obj: Upload) -> str:
        return self._absolute_url(obj)

    def get_file_url(self, obj: Upload) -> str:
        return self._absolute_url(obj)


class UploadCreateSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)
    conversation_id = serializers.UUIDField(required=False, allow_null=True)
