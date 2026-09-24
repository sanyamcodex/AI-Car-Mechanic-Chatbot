from django.conf import settings
from django.urls import path, include, re_path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/', include('apps.core.urls')),
    path('api/', include('apps.kb.urls')),
    path('api/', include('apps.chat.urls')),
    path('api/', include('apps.uploads.urls')),
    path('api/', include('apps.diagnosis.urls')),
    path('api/', include('apps.booking.urls')),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
