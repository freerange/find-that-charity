import json

from starlette.testclient import TestClient

from findthatcharity.app import app

def test_reconcile():
    client = TestClient(app)
    response = client.get('/reconcile')
    assert response.status_code == 200
    result = response.json()
    assert result["identifierSpace"] == "http://rdf.freebase.com/ns/type.object.id"

def test_reconcile_query():
    client = TestClient(app)
    response = client.get('/reconcile?query=ncvo')
    assert response.status_code == 200
    result = response.json()
    assert result["total"] == 1
    assert len(result["result"]) == 1
    assert result["result"][0]["id"] == "225922"

def test_reconcile_query_callback():
    client = TestClient(app)
    response = client.get('/reconcile?query=ncvo&callback=test_func')
    assert response.status_code == 200
    result = response.text
    assert result.startswith("test_func(")
    assert result.endswith(");")
    assert "225922" in result

def test_reconcile_queries():
    client = TestClient(app)
    response = client.get('/reconcile?queries={"q0":{"query":"ncvo"},"q1":{"query":"acevo"}}')
    assert response.status_code == 200
    result = response.json()
    assert len(result) == 2
    assert "q0" in result.keys()
    assert "q1" in result.keys()
    assert result["q0"]["result"][0]["id"] == "225922"
    assert result["q1"]["result"][0]["id"] == "1114591"


def test_reconcile_queries_callback():
    client = TestClient(app)
    data = {'queries': '{"q0":{"query":"ncvo"},"q1":{"query":"acevo"}}'}
    response = client.post('/reconcile?callback=test_func', data=data)
    if response.status_code==302:
        response = client.post(response.headers['location'], data=data)
    print(response.headers)
    assert response.status_code == 200
    result = response.text
    assert result.startswith("test_func(")
    assert result.endswith(");")
    assert "225922" in result

def test_reconcile_extend():
    client = TestClient(app)
    data = {
        "ids": ["225922", "123456"],
        "properties": [
            {"id": "known_as"},
            {"id": "geo.postcode"},
        ]
    }
    response = client.get('/reconcile?extend={}'.format(json.dumps(data)))
    assert response.status_code == 200
    result = response.json()
    assert len(result["meta"]) == 2
    assert len(result["rows"]) == 2
    assert len(result["rows"]["225922"]) == 2
    assert len(result["rows"]["123456"]) == 2
    assert len(result["rows"]["123456"]["known_as"]) == 0
    assert len(result["rows"]["225922"]["known_as"])

def test_propose_properties():
    client = TestClient(app)
    response = client.get('/reconcile/propose_properties')
    assert response.status_code == 200
    result = response.json()
    assert len(result["properties"])==19

def test_propose_properties_callback():
    client = TestClient(app)
    response = client.get('/reconcile/propose_properties?callback=test_func')
    assert response.status_code == 200
    result = response.text
    assert result.startswith("test_func(")
    assert result.endswith(");")
