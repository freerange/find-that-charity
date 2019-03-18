from starlette.testclient import TestClient

from findthatcharity.app import app

def test_charity_missing():
    client = TestClient(app)
    response = client.get('/charity/ABCDASD')
    assert response.status_code == 404
    assert "not found" in response.text.lower()

def test_charity_inactive():
    client = TestClient(app)
    response = client.get('/charity/1143497')
    assert response.status_code == 200
    assert "inactive" in response.text.lower()

def test_charity_preview():
    client = TestClient(app)
    response = client.get('/charity/225922/preview')
    assert response.status_code == 200
    assert "National Council for Voluntary Organisations".lower() in response.text.lower()

def test_charity_json():
    client = TestClient(app)
    response = client.get('/charity/225922.json')
    assert response.status_code == 200
    result = response.json()
    assert result["known_as"] == "The National Council for Voluntary Organisations"

def test_charity():
    client = TestClient(app)
    response = client.get('/charity/225922.html')
    assert response.status_code == 200
    assert "National Council for Voluntary Organisations".lower() in response.text.lower()
