from django.urls import path
from apps.booking.views import BookingView, BookingDetailView

urlpatterns = [
    path('booking/', BookingView.as_view(), name='booking'),
    path('booking/<uuid:pk>/', BookingDetailView.as_view(), name='booking-detail'),
]
