from starlette.testclient import TestClient

from findthatcharity.app import app

def test_random():
    client = TestClient(app)
    response = client.get('/random')
    assert response.status_code == 200
    assert "/orgid/" in response.url

def test_random_active():
    client = TestClient(app)
    response = client.get('/random?active')
    assert response.status_code == 200
    assert "inactive" not in response.text

def test_random_json():
    client = TestClient(app)
    response = client.get('/random.json')
    assert response.status_code == 200
    result = response.json()
