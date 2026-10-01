import pytest

from app import app


@pytest.fixture
def client():
    return app.test_client()


def test_health(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.data.decode() == "CodeJudge app is running successfully!"


def test_home(client):
    response = client.get('/')
    assert response.status_code == 200