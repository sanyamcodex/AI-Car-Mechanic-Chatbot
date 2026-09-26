import logging
from typing import Any
from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    MethodNotAllowed,
    NotAcceptable,
    UnsupportedMediaType,
    Throttled,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class ApiException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'validation_error'
    default_detail = 'An error occurred.'

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        fields: dict[str, list[str]] | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(detail=message, code=code)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.fields = fields or {}
        self.details = details or {}


def format_error_dict(
    code: str,
    message: str,
    fields: dict[str, list[str]] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        'error': {
            'code': code,
            'message': message,
            'fields': fields if fields is not None else {},
            'details': details if details is not None else {},
        }
    }


def make_error_response(
    code: str,
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    fields: dict[str, list[str]] | None = None,
    details: dict[str, Any] | None = None,
) -> Response:
    return Response(
        format_error_dict(code=code, message=message, fields=fields, details=details),
        status=status_code,
    )


def handler404(request, exception=None):
    return JsonResponse(
        format_error_dict(code='not_found', message='The requested resource was not found.'),
        status=status.HTTP_404_NOT_FOUND,
    )


def handler500(request):
    return JsonResponse(
        format_error_dict(code='server_error', message='An unexpected error occurred. Please try again later.'),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _normalize_validation_fields(data: Any) -> tuple[str, dict[str, list[str]]]:
    message = 'Validation failed.'
    fields: dict[str, list[str]] = {}

    if isinstance(data, dict):
        if 'detail' in data and len(data) == 1:
            message = str(data['detail'])
        elif 'non_field_errors' in data:
            non_fields = data.get('non_field_errors', [])
            if isinstance(non_fields, list) and non_fields:
                message = str(non_fields[0])
            fields['non_field_errors'] = [str(e) for e in (non_fields if isinstance(non_fields, list) else [non_fields])]

        for key, value in data.items():
            if key in ('detail', 'non_field_errors'):
                continue
            if isinstance(value, list):
                fields[key] = [str(item) for item in value]
            elif isinstance(value, dict):
                sub_msg, sub_fields = _normalize_validation_fields(value)
                for sub_k, sub_v in sub_fields.items():
                    fields[f"{key}.{sub_k}"] = sub_v
            else:
                fields[key] = [str(value)]

        if message == 'Validation failed.' and fields:
            first_key = next(iter(fields))
            if fields[first_key]:
                message = f"{first_key}: {fields[first_key][0]}"
    elif isinstance(data, list):
        if data:
            message = str(data[0])
        fields['non_field_errors'] = [str(item) for item in data]
    else:
        message = str(data)

    return message, fields


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, ApiException):
        return Response(
            format_error_dict(
                code=exc.code,
                message=exc.message,
                fields=exc.fields,
                details=exc.details,
            ),
            status=exc.status_code,
        )

    response = exception_handler(exc, context)

    if response is not None:
        status_code = response.status_code
        data = response.data
        code = 'validation_error'
        message = 'Invalid request.'
        fields: dict[str, list[str]] = {}
        details: dict[str, Any] = {}

        if status_code == status.HTTP_404_NOT_FOUND:
            code = 'not_found'
            message = str(data.get('detail', 'Resource not found.')) if isinstance(data, dict) else 'Resource not found.'
        elif status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            code = 'rate_limited'
            message = str(data.get('detail', 'Request was throttled.')) if isinstance(data, dict) else 'Rate limit exceeded.'
        elif status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE:
            code = 'unsupported_media'
            message = str(data.get('detail', 'Unsupported media type.')) if isinstance(data, dict) else 'Unsupported media type.'
        elif status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE:
            code = 'payload_too_large'
            message = 'Payload too large.'
        elif status_code == status.HTTP_409_CONFLICT:
            code = 'conflict'
            message = str(data.get('detail', 'Conflict occurred.')) if isinstance(data, dict) else 'Conflict occurred.'
        elif status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN):
            code = 'permission_denied'
            message = str(data.get('detail', 'Permission denied.')) if isinstance(data, dict) else 'Permission denied.'
        elif status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
            code = 'method_not_allowed'
            message = str(data.get('detail', 'Method not allowed.')) if isinstance(data, dict) else 'Method not allowed.'
        elif status_code == status.HTTP_400_BAD_REQUEST:
            code = 'validation_error'
            message, fields = _normalize_validation_fields(data)
        else:
            if isinstance(data, dict) and 'detail' in data:
                message = str(data['detail'])

        response.data = format_error_dict(
            code=code,
            message=message,
            fields=fields,
            details=details,
        )
        return response

    if isinstance(exc, Http404):
        return Response(
            format_error_dict(code='not_found', message=str(exc) or 'Not found.'),
            status=status.HTTP_404_NOT_FOUND,
        )

    if isinstance(exc, PermissionDenied):
        return Response(
            format_error_dict(code='permission_denied', message='Permission denied.'),
            status=status.HTTP_403_FORBIDDEN,
        )

    logger.exception("Unhandled server exception: %s", exc)
    return Response(
        format_error_dict(
            code='server_error',
            message='An unexpected error occurred. Please try again later.',
        ),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
