import json
from tests.conftest import login
from app.models import User, Task, Note, Notification, Resource
from app.extensions import db

def test_user_data_export(client, student, app):
    login(client)
    # Create sample task and note
    client.post('/api/tasks', json={'title': 'My Task', 'category': 'project', 'priority': 'high'})
    client.post('/api/notes', json={'title': 'My Note', 'content': 'Secret thoughts', 'subject': 'Biology'})

    # Create a notification
    with app.app_context():
        db.session.add(Notification(user_id=student, title='Welcome', message='Welcome to CampusHub', kind='info'))
        db.session.commit()

    # Web export download
    resp = client.get('/profile/export')
    assert resp.status_code == 200
    assert resp.mimetype == 'application/json'
    assert 'attachment' in resp.headers.get('Content-Disposition', '')
    assert 'campus_hub_data_export.json' in resp.headers.get('Content-Disposition', '')

    data = json.loads(resp.data)
    assert data['user']['id'] == student
    assert data['user']['email'] == 'student@test.local'
    assert data['user']['name'] == 'Test Student'
    assert data['user']['role'] == 'student'
    assert 'joined_at' in data['user']

    assert len(data['tasks']) == 1
    assert data['tasks'][0]['title'] == 'My Task'
    assert data['tasks'][0]['priority'] == 'high'
    assert data['tasks'][0]['category'] == 'project'
    assert data['tasks'][0]['completed'] is False
    assert 'created_at' in data['tasks'][0]

    assert len(data['notes']) == 1
    assert data['notes'][0]['title'] == 'My Note'
    assert data['notes'][0]['content'] == 'Secret thoughts'
    assert data['notes'][0]['subject'] == 'Biology'

    assert len(data['notifications']) == 1
    assert data['notifications'][0]['title'] == 'Welcome'
    assert data['notifications'][0]['message'] == 'Welcome to CampusHub'

    # API export
    resp_api = client.get('/api/user/export')
    assert resp_api.status_code == 200
    assert resp_api.is_json
    data_api = resp_api.get_json()['data']
    assert data_api['user']['email'] == 'student@test.local'
    assert len(data_api['tasks']) == 1
    assert len(data_api['notes']) == 1
    assert len(data_api['notifications']) == 1

def test_user_data_export_unauthenticated(client):
    # Web endpoint requires login
    assert client.get('/profile/export').status_code == 302
    # API endpoint returns 401
    assert client.get('/api/user/export').status_code == 401

def test_account_deletion_web_route(client, student, app):
    login(client)
    client.post('/api/tasks', json={'title': 'To be deleted'})
    client.post('/api/notes', json={'title': 'Note to delete', 'content': 'bye'})

    with app.app_context():
        res = Resource(title='Shared Resource', url='https://example.com', added_by=student)
        notif = Notification(user_id=student, title='Reminder', message='Check tasks')
        db.session.add_all([res, notif])
        db.session.commit()
        res_id = res.id

    # 1. Reject deletion if wrong password provided
    resp = client.post('/profile/delete-account', data={'password': 'WrongPassword123'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Incorrect password' in resp.data

    with app.app_context():
        assert db.session.get(User, student) is not None
        assert Task.query.filter_by(user_id=student).count() == 1
        assert Note.query.filter_by(user_id=student).count() == 1
        assert Notification.query.filter_by(user_id=student).count() == 1

    # 2. Reject deletion if password field is missing or empty
    resp_empty = client.post('/profile/delete-account', data={'password': ''}, follow_redirects=True)
    assert resp_empty.status_code == 200
    assert b'Incorrect password' in resp_empty.data

    # 3. Successful deletion with correct password
    resp = client.post('/profile/delete-account', data={'password': 'Password123'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'permanently deleted' in resp.data

    # Verify user and related records are completely wiped from DB
    with app.app_context():
        assert db.session.get(User, student) is None
        assert Task.query.filter_by(user_id=student).count() == 0
        assert Note.query.filter_by(user_id=student).count() == 0
        assert Notification.query.filter_by(user_id=student).count() == 0
        # Resource remains, but added_by foreign key is safely cleared to None
        res_after = db.session.get(Resource, res_id)
        assert res_after is not None
        assert res_after.added_by is None

    # Subsequent access is unauthenticated
    resp_profile = client.get('/profile')
    assert resp_profile.status_code == 302

    # Subsequent login with old credentials fails
    resp_login = client.post('/login', data={'email': 'student@test.local', 'password': 'Password123'}, follow_redirects=True)
    assert b'Invalid email or password' in resp_login.data

    # The freed email can now be registered again cleanly
    resp_reg = client.post('/api/auth/register', json={
        'name': 'New Student',
        'email': 'student@test.local',
        'password': 'Password123'
    })
    assert resp_reg.status_code == 201

def test_account_deletion_web_unauthenticated(client):
    resp = client.post('/profile/delete-account', data={'password': 'Password123'})
    assert resp.status_code == 302

def test_account_deletion_api(client, student, app):
    login(client)

    with app.app_context():
        db.session.add(Notification(user_id=student, title='Alert', message='Test'))
        db.session.commit()

    # 1. Wrong password
    resp = client.delete('/api/user/account', json={'password': 'WrongPassword'})
    assert resp.status_code == 400
    assert 'Incorrect password' in resp.get_json()['error']

    # 2. Empty password
    resp = client.delete('/api/user/account', json={'password': ''})
    assert resp.status_code == 400
    assert 'Incorrect password' in resp.get_json()['error']

    # User still exists
    with app.app_context():
        assert db.session.get(User, student) is not None

    # 3. Correct password
    resp = client.delete('/api/user/account', json={'password': 'Password123'})
    assert resp.status_code == 200
    assert resp.get_json()['success'] is True
    assert 'deleted successfully' in resp.get_json()['data']['message']

    with app.app_context():
        assert db.session.get(User, student) is None
        assert Notification.query.filter_by(user_id=student).count() == 0

def test_account_deletion_api_post_method(client, student, app):
    login(client)

    # Allow POST as well as DELETE on API endpoint
    resp = client.post('/api/user/account', json={'password': 'Password123'})
    assert resp.status_code == 200
    assert resp.get_json()['success'] is True

    with app.app_context():
        assert db.session.get(User, student) is None

def test_account_deletion_api_unauthenticated(client):
    assert client.delete('/api/user/account', json={'password': 'Password123'}).status_code == 401

def test_profile_page_ui(client, student):
    login(client)
    resp = client.get('/profile')
    assert resp.status_code == 200
    assert b'Data &amp; Privacy' in resp.data or b'Data & Privacy' in resp.data
    assert b'/profile/export' in resp.data
    assert b'/profile/delete-account' in resp.data
    assert b'Permanently Delete Account' in resp.data
