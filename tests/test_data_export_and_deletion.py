import json
from tests.conftest import login
from app.models import User, Task, Note, Notification
from app.extensions import db

def test_user_data_export(client, student, app):
    login(client)
    client.post('/api/tasks', json={'title': 'My Task', 'category': 'project'})
    client.post('/api/notes', json={'title': 'My Note', 'content': 'Secret thoughts'})

    # Web export
    resp = client.get('/profile/export')
    assert resp.status_code == 200
    assert 'attachment' in resp.headers.get('Content-Disposition', '')
    data = json.loads(resp.data)
    assert data['user']['email'] == 'student@test.local'
    assert len(data['tasks']) == 1
    assert data['tasks'][0]['title'] == 'My Task'
    assert len(data['notes']) == 1
    assert data['notes'][0]['title'] == 'My Note'

    # API export
    resp_api = client.get('/api/user/export')
    assert resp_api.status_code == 200
    data_api = resp_api.get_json()['data']
    assert data_api['user']['email'] == 'student@test.local'
    assert len(data_api['tasks']) == 1

def test_user_data_export_unauthenticated(client):
    assert client.get('/profile/export').status_code == 302
    assert client.get('/api/user/export').status_code == 401

def test_account_deletion_web_route(client, student, app):
    login(client)
    client.post('/api/tasks', json={'title': 'To be deleted'})
    client.post('/api/notes', json={'title': 'Note to delete', 'content': 'bye'})

    # Try deleting with wrong password
    resp = client.post('/profile/delete-account', data={'password': 'WrongPassword123'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Incorrect password' in resp.data

    with app.app_context():
        assert db.session.get(User, student) is not None

    # Delete with correct password
    resp = client.post('/profile/delete-account', data={'password': 'Password123'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'permanently deleted' in resp.data

    # Verify user and related records are gone
    with app.app_context():
        assert db.session.get(User, student) is None
        assert Task.query.filter_by(user_id=student).count() == 0
        assert Note.query.filter_by(user_id=student).count() == 0

def test_account_deletion_api(client, student, app):
    login(client)

    # Wrong password
    resp = client.delete('/api/user/account', json={'password': 'WrongPassword'})
    assert resp.status_code == 400
    assert 'Incorrect password' in resp.get_json()['error']

    # Correct password
    resp = client.delete('/api/user/account', json={'password': 'Password123'})
    assert resp.status_code == 200
    assert resp.get_json()['success'] is True

    with app.app_context():
        assert db.session.get(User, student) is None
