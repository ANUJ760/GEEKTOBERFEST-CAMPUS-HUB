from tests.conftest import login
from app.models import Task, Note
from app.extensions import db

def test_full_text_search_api(client, student):
    login(client)
    client.post('/api/tasks', json={'title': 'Calculus Assignment 1', 'description': 'Solve limits and derivatives', 'category': 'assignment'})
    client.post('/api/tasks', json={'title': 'History Essay', 'description': 'WWII summary', 'category': 'assignment'})
    client.post('/api/notes', json={'title': 'Calculus Lecture 2', 'content': 'Integration techniques and substitutions', 'subject': 'Math'})

    # Search for 'Calculus'
    resp = client.get('/api/search?q=Calculus')
    assert resp.status_code == 200
    data = resp.get_json()['data']
    assert data['total'] == 2
    assert len(data['tasks']) == 1
    assert data['tasks'][0]['title'] == 'Calculus Assignment 1'
    assert len(data['notes']) == 1
    assert data['notes'][0]['title'] == 'Calculus Lecture 2'

    # Filter tasks only
    resp = client.get('/api/search?q=Calculus&type=tasks')
    data = resp.get_json()['data']
    assert len(data['tasks']) == 1
    assert len(data['notes']) == 0

    # Filter notes only
    resp = client.get('/api/search?q=Calculus&type=notes')
    data = resp.get_json()['data']
    assert len(data['tasks']) == 0
    assert len(data['notes']) == 1

def test_full_text_search_privacy_scoping(client, student, admin, app):
    # Student creates private content
    login(client, 'student@test.local')
    client.post('/api/tasks', json={'title': 'Secret Project Alpha', 'description': 'Confidential task'})
    client.post('/api/notes', json={'title': 'Secret Diary', 'content': 'Classified student notes'})
    client.post('/logout')

    # Admin searches for 'Secret'
    login(client, 'admin@test.local')
    resp = client.get('/api/search?q=Secret')
    assert resp.status_code == 200
    data = resp.get_json()['data']
    assert data['total'] == 0
    assert len(data['tasks']) == 0
    assert len(data['notes']) == 0

def test_full_text_search_web_route(client, student):
    login(client)
    client.post('/api/tasks', json={'title': 'Biology Lab', 'description': 'Microscope dissection'})

    # Empty query
    resp = client.get('/search')
    assert resp.status_code == 200
    assert b'Enter keywords above' in resp.data

    # Query matching item
    resp = client.get('/search?q=Biology')
    assert resp.status_code == 200
    assert b'Biology Lab' in resp.data
    assert b'Microscope dissection' in resp.data

def test_full_text_search_unauthenticated(client):
    assert client.get('/search').status_code == 302
    assert client.get('/api/search?q=test').status_code == 401
