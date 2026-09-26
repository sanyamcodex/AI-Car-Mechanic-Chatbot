import pytest
from rest_framework.test import APIClient
from django.urls import reverse


@pytest.mark.django_db
def test_health_check_endpoint():
    client = APIClient()
    response = client.get(reverse('health'))
    assert response.status_code == 200
    data = response.json()
    assert data == {'status': 'ok', 'db': True}


@pytest.mark.django_db
def test_error_envelope_404_not_found():
    client = APIClient()
    response = client.get('/api/non-existent-endpoint/')
    assert response.status_code == 404
    data = response.json()
    assert 'error' in data
    error = data['error']
    assert error['code'] == 'not_found'
    assert isinstance(error['message'], str)
    assert isinstance(error['fields'], dict)
    assert isinstance(error['details'], dict)
