from starlette.testclient import TestClient

from findthatcharity.app import app

def test_feed_atom():
    client = TestClient(app)
    response = client.get('/feeds/ccew.atom')
    assert response.status_code == 200
    assert "Charity Commission for England and Wales data downloads".lower() in response.text.lower()

def test_feed_rss():
    client = TestClient(app)
    response = client.get('/feeds/ccew.rss')
    assert response.status_code == 200
    assert "Charity Commission for England and Wales data downloads".lower() in response.text.lower()

def test_feed_json():
    client = TestClient(app)
    response = client.get('/feeds/ccew.json')
    assert response.status_code == 200
    response.json()
