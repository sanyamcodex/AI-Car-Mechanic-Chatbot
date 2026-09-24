from rest_framework.throttling import ScopedRateThrottle


class AnonRateThrottle(ScopedRateThrottle):
    scope = 'anon'


class ChatRateThrottle(ScopedRateThrottle):
    scope = 'chat'


class UploadRateThrottle(ScopedRateThrottle):
    scope = 'upload'


class BookingRateThrottle(ScopedRateThrottle):
    scope = 'booking'
