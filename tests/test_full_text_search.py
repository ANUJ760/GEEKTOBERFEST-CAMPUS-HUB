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

def test_full_text_search_relevance_ranking(client, student):
    login(client)
    # Task with keyword in title vs task with keyword only in description
    client.post('/api/tasks', json={'title': 'Biology Exam Preparation', 'description': 'Review chapters 1 through 5'})
    client.post('/api/tasks', json={'title': 'Weekend Chores', 'description': 'Clean desk and organize biology flashcards'})

    resp = client.get('/api/search?q=Biology&type=tasks')
    assert resp.status_code == 200
    tasks = resp.get_json()['data']['tasks']
    assert len(tasks) == 2
    # Title match should be ranked first due to higher relevance score
    assert tasks[0]['title'] == 'Biology Exam Preparation'
    assert tasks[1]['title'] == 'Weekend Chores'

    # Note with keyword in title vs note with keyword only in content
    client.post('/api/notes', json={'title': 'Organic Chemistry Guide', 'content': 'Alkene reactions and reagents', 'subject': 'Chemistry'})
    client.post('/api/notes', json={'title': 'General Study Tips', 'content': 'Techniques for organic chemistry memorization', 'subject': 'Study'})

    resp_notes = client.get('/api/search?q=Organic&type=notes')
    assert resp_notes.status_code == 200
    notes = resp_notes.get_json()['data']['notes']
    assert len(notes) == 2
    assert notes[0]['title'] == 'Organic Chemistry Guide'
    assert notes[1]['title'] == 'General Study Tips'

def test_full_text_search_multi_token_and_matching(client, student):
    login(client)
    client.post('/api/tasks', json={'title': 'Physics Quantum Mechanics', 'description': 'Schrodinger equation practice'})
    client.post('/api/tasks', json={'title': 'Physics Classical Mechanics', 'description': 'Newton laws'})

    # Query with multiple tokens requiring both terms
    resp = client.get('/api/search?q=Physics+Quantum')
    assert resp.status_code == 200
    tasks = resp.get_json()['data']['tasks']
    assert len(tasks) == 1
    assert tasks[0]['title'] == 'Physics Quantum Mechanics'

def test_full_text_search_exact_phrase(client, student):
    login(client)
    client.post('/api/notes', json={'title': 'Modern Computing', 'content': 'We study artificial intelligence and deep learning.'})
    client.post('/api/notes', json={'title': 'Misc Notes', 'content': 'Intelligence is an artificial concept sometimes.'})

    resp = client.get('/api/search?q="artificial+intelligence"')
    assert resp.status_code == 200
    notes = resp.get_json()['data']['notes']
    assert len(notes) == 1
    assert notes[0]['title'] == 'Modern Computing'

def test_full_text_search_privacy_scoping(client, student, admin, app):
    # Student creates private content
    login(client, 'student@test.local')
    client.post('/api/tasks', json={'title': 'Secret Project Alpha', 'description': 'Confidential task'})
    client.post('/api/notes', json={'title': 'Secret Diary', 'content': 'Classified student notes'})
    client.post('/logout')

    # Admin searches for 'Secret' - must not see student's records
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

    # Empty query shows initial prompt
    resp = client.get('/search')
    assert resp.status_code == 200
    assert b'Enter keywords above' in resp.data

    # Query matching item
    resp = client.get('/search?q=Biology')
    assert resp.status_code == 200
    assert b'Biology Lab' in resp.data
    assert b'Microscope dissection' in resp.data

    # Query with no match
    resp_empty = client.get('/search?q=NonExistentSubject999')
    assert resp_empty.status_code == 200
    assert b'No tasks or notes match your search' in resp_empty.data

def test_full_text_search_unauthenticated(client):
    assert client.get('/search').status_code == 302
    assert client.get('/api/search?q=test').status_code == 401

def test_full_text_search_api_post(client, student):
    login(client)
    client.post('/api/tasks', json={'title': 'Math Homework', 'description': 'Page 42'})

    # API POST request support
    resp = client.post('/api/search', json={'q': 'Math'})
    assert resp.status_code == 200
    data = resp.get_json()['data']
    assert data['total'] == 1
    assert data['tasks'][0]['title'] == 'Math Homework'

def test_full_text_search_parameter_compatibility(client, student):
    login(client)
    client.post('/api/notes', json={'title': 'Literature Notes', 'content': 'Shakespeare sonnets'})

    # Test 'search' parameter compatibility with 'q'
    resp_search = client.get('/api/search?search=Shakespeare')
    resp_q = client.get('/api/search?q=Shakespeare')
    assert resp_search.status_code == 200
    assert resp_q.status_code == 200
    assert resp_search.get_json()['data']['total'] == resp_q.get_json()['data']['total'] == 1

def test_full_text_search_special_characters_and_safety(client, student):
    login(client)
    client.post('/api/tasks', json={'title': 'Score 100% On Test', 'description': 'Target is 100% correct'})
    client.post('/api/notes', json={'title': 'HTML Notes', 'content': 'Use <div> and <script> tags'})

    # Query with SQL wildcards (% and _)
    resp = client.get('/api/search?q=100%')
    assert resp.status_code == 200
    assert resp.get_json()['data']['total'] == 1

    # HTML tags in snippet are escaped, XSS safe
    resp_xss = client.get('/api/search?q=script')
    assert resp_xss.status_code == 200
    snippet = resp_xss.get_json()['data']['notes'][0]['snippet']
    assert '<script>' not in snippet
    assert '&lt;' in snippet or '&gt;' in snippet or '<mark>' in snippet

def test_full_text_search_case_insensitivity(client, student):
    login(client)
    client.post('/api/tasks', json={'title': 'Robotics Lab', 'description': 'Arduino programming'})

    resp_lower = client.get('/api/search?q=robotics')
    resp_upper = client.get('/api/search?q=ROBOTICS')
    resp_mixed = client.get('/api/search?q=RoBoTiCs')

    assert resp_lower.get_json()['data']['total'] == 1
    assert resp_upper.get_json()['data']['total'] == 1
    assert resp_mixed.get_json()['data']['total'] == 1
