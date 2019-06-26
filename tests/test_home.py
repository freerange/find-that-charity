from starlette.testclient import TestClient

from findthatcharity.app import app

def test_home():
    client = TestClient(app)
    response = client.get('/')
    assert response.status_code == 200
    assert "Find that charity" in response.text

def test_home_search():
    client = TestClient(app)
    response = client.get('/?q=ncvo')
    assert response.status_code == 200
    assert "225922" in response.text

def test_about():
    client = TestClient(app)
    response = client.get('/about')
    assert response.status_code == 200
    assert "Data sources" in response.text

    # check regulators are acknowledged
    assert "Charity Commission for England and Wales" in response.text
    assert "Office of Scottish Charity Regulator" in response.text
    assert "Charity Commission for Northern Ireland" in response.text
