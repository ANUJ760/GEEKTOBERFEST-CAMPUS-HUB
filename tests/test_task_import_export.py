import io
import json
from datetime import date
from tests.conftest import login
from app.models import Task, User
from app.extensions import db

def test_task_export_api(client, student):
    login(client)
    client.post('/api/tasks', json={'title': 'Assignment 1', 'description': 'Math homework', 'priority': 'high', 'category': 'assignment', 'due_date': '2026-10-25'})
    client.post('/api/tasks', json={'title': 'Exam Prep', 'priority': 'medium', 'category': 'exam'})

    resp = client.get('/api/tasks/export')
    assert resp.status_code == 200
    assert 'attachment' in resp.headers.get('Content-Disposition', '')
    data = resp.get_json()['data']
    assert len(data) == 2
    titles = [t['title'] for t in data]
    assert 'Assignment 1' in titles
    assert 'Exam Prep' in titles

def test_task_export_route(client, student):
    login(client)
    client.post('/api/tasks', json={'title': 'Project Draft', 'priority': 'low', 'category': 'project'})
    resp = client.get('/tasks/export')
    assert resp.status_code == 200
    assert 'tasks.json' in resp.headers.get('Content-Disposition', '')
    tasks = json.loads(resp.data)
    assert len(tasks) == 1
    assert tasks[0]['title'] == 'Project Draft'

def test_task_export_user_scoping(client, student, admin, app):
    # Student creates a task
    login(client, 'student@test.local')
    client.post('/api/tasks', json={'title': 'Student Task'})
    client.post('/logout')

    # Admin creates a task
    login(client, 'admin@test.local')
    client.post('/api/tasks', json={'title': 'Admin Task'})

    # Admin export should only contain Admin Task
    resp = client.get('/api/tasks/export')
    data = resp.get_json()['data']
    assert len(data) == 1
    assert data[0]['title'] == 'Admin Task'

def test_task_import_api_json_list(client, student):
    login(client)
    payload = [
        {'title': 'Imported 1', 'description': 'First', 'priority': 'high', 'category': 'exam', 'due_date': '2026-11-01', 'completed': False, 'user_id': 9999},
        {'title': 'Imported 2', 'priority': 'low', 'category': 'personal', 'completed': True}
    ]
    resp = client.post('/api/tasks/import', json=payload)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body['data']['imported_count'] == 2

    # Verify in DB and verify user_id scoping
    t_resp = client.get('/api/tasks')
    tasks = t_resp.get_json()['data']
    assert len(tasks) == 2
    t1 = next(t for t in tasks if t['title'] == 'Imported 1')
    assert t1['priority'] == 'high'
    assert t1['category'] == 'exam'
    assert t1['due_date'] == '2026-11-01'
    assert t1['completed'] is False

def test_task_import_api_tasks_wrapper(client, student):
    login(client)
    payload = {
        'tasks': [
            {'title': 'Wrapped Task', 'priority': 'medium', 'category': 'project'}
        ]
    }
    resp = client.post('/api/tasks/import', json=payload)
    assert resp.status_code == 201
    assert resp.get_json()['data']['imported_count'] == 1

def test_task_import_validation_errors(client, student):
    login(client)

    # Missing title
    resp = client.post('/api/tasks/import', json=[{'description': 'No title'}])
    assert resp.status_code == 400
    assert 'missing a title' in resp.get_json()['error']

    # Invalid priority
    resp = client.post('/api/tasks/import', json=[{'title': 'Valid', 'priority': 'super-high'}])
    assert resp.status_code == 400
    assert 'invalid priority' in resp.get_json()['error']

    # Invalid category
    resp = client.post('/api/tasks/import', json=[{'title': 'Valid', 'category': 'unknown'}])
    assert resp.status_code == 400
    assert 'invalid category' in resp.get_json()['error']

    # Invalid due date format
    resp = client.post('/api/tasks/import', json=[{'title': 'Valid', 'due_date': '15-10-2026'}])
    assert resp.status_code == 400
    assert 'invalid due date format' in resp.get_json()['error']

    # Empty list
    resp = client.post('/api/tasks/import', json=[])
    assert resp.status_code == 400

    # Non-list and non-dict
    resp = client.post('/api/tasks/import', json="not a json object")
    assert resp.status_code == 400

def test_task_import_web_form(client, student):
    login(client)
    file_content = json.dumps([
        {'title': 'Web Upload Task', 'priority': 'medium', 'category': 'other'}
    ]).encode('utf-8')
    data = {
        'file': (io.BytesIO(file_content), 'tasks.json')
    }
    resp = client.post('/tasks/import', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Successfully imported 1 task' in resp.data

    # Verify task was created
    t_resp = client.get('/api/tasks')
    assert len(t_resp.get_json()['data']) == 1
