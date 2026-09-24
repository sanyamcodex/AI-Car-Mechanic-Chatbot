from django.urls import path
from apps.uploads.views import UploadView, UploadDetailView

urlpatterns = [
    # Canonical endpoint per assessment specification
    path('upload/', UploadView.as_view(), name='upload'),
    path('upload/<uuid:pk>/', UploadDetailView.as_view(), name='upload-detail'),
    # Backwards-compatible aliases
    path('uploads/', UploadView.as_view(), name='uploads'),
    path('uploads/<uuid:pk>/', UploadDetailView.as_view(), name='uploads-detail'),
]
