from starlette.testclient import TestClient

from findthatcharity.app import app

def test_charity_missing():
    client = TestClient(app)
    response = client.get('/adddata')
    assert response.status_code == 200
    assert "id='reconcile-root'" in response.text.lower()