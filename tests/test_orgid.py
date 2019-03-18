from starlette.testclient import TestClient

from findthatcharity.app import app

def test_orgid_missing():
    client = TestClient(app)
    response = client.get('/orgid/ABCDASD')
    assert response.status_code == 404
    assert "not found" in response.text.lower()

def test_orgid_json():
    client = TestClient(app)
    response = client.get('/orgid/GB-COH-00198344.json')
    assert response.status_code == 200
    result = response.json()
    assert result["known_as"] == "The National Council for Voluntary Organisations"

def test_orgid():
    client = TestClient(app)
    response = client.get('/orgid/GB-COH-00198344')
    assert response.url.endswith('/charity/225922')
