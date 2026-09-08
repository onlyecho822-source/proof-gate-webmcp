from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get('/healthz')
    assert r.status_code == 200
    assert r.json()['ok'] is True
    assert r.json()['version'] == '0.3.0'


def test_demo_route_exposes_router_revision_and_server_decision_id():
    r = client.get('/api/demo')
    assert r.status_code == 200
    body = r.json()
    assert body['decision_id']
    assert body['decision']['current_status'] in {'HOLD', 'CONDITIONAL'}
    assert body['decision']['mode_trace'][0]['mode'] == 'NATE'
    assert body['decision']['architecture_version'] == '0.3.0'
    assert body['decision']['research_requests']


def test_live_route_fails_closed_without_parallel_key(monkeypatch):
    monkeypatch.delenv('PARALLEL_API_KEY', raising=False)
    package = client.get('/api/demo').json()['package']
    r = client.post('/api/analyze', json={'package': package, 'live_research': True})
    assert r.status_code == 424


def test_authority_endpoint_applies_server_issued_recommended_world_and_reverifies():
    demo = client.get('/api/demo').json()
    decision = demo['decision']
    world_id = decision['recommended_world_id']
    r = client.post('/api/authority', json={
        'decision_id': demo['decision_id'],
        'world_id': world_id,
        'approved': True,
        'note': 'Demo producer approval',
    })
    assert r.status_code == 200
    body = r.json()
    assert body['approved'] is True
    assert body['case_revision'] == 2
    assert body['decision_id'] != demo['decision_id']
    assert body['decision']['current_status'] == 'GREENLIGHT'
    assert body['decision']['case_revision'] == 2


def test_authority_rejection_does_not_mutate():
    demo = client.get('/api/demo').json()
    world_id = demo['decision']['recommended_world_id']
    r = client.post('/api/authority', json={
        'decision_id': demo['decision_id'], 'world_id': world_id, 'approved': False,
    })
    assert r.status_code == 200
    assert r.json()['next_state'] == 'HOLD'


def test_authority_rejects_client_invented_world():
    demo = client.get('/api/demo').json()
    r = client.post('/api/authority', json={
        'decision_id': demo['decision_id'], 'world_id': 'world-evil-invented', 'approved': True,
    })
    assert r.status_code == 400
    assert 'server-issued' in r.json()['detail']


def test_authority_rejects_expired_or_unknown_snapshot():
    r = client.post('/api/authority', json={
        'decision_id': 'missing', 'world_id': 'world-01', 'approved': True,
    })
    assert r.status_code == 409
