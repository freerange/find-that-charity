from starlette.testclient import TestClient

from findthatcharity.app import app

def test_autocomplete_blank():
    client = TestClient(app)
    response = client.get('/autocomplete')
    assert response.status_code == 200
    result = response.json()
    assert len(result["results"])==0

def test_autocomplete_blank():
    client = TestClient(app)
    response = client.get('/autocomplete?q=nc')
    assert response.status_code == 200
    result = response.json()
    assert len(result["results"])>0
