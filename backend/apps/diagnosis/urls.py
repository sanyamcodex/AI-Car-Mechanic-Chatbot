from django.urls import path
from apps.diagnosis.views import DiagnosisView, DiagnosisDetailView

urlpatterns = [
    path('diagnosis/', DiagnosisView.as_view(), name='diagnosis'),
    path('diagnosis/<uuid:pk>/', DiagnosisDetailView.as_view(), name='diagnosis-detail'),
]
