from django.urls import path
from apps.uploads.views import UploadView, UploadDetailView

urlpatterns = [
    path('uploads/', UploadView.as_view(), name='uploads'),
    path('uploads/<uuid:pk>/', UploadDetailView.as_view(), name='upload-detail'),
]
