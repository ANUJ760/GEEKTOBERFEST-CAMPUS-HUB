import json
from tests.conftest import login

def test_task_crud_and_ownership(client,student,app):
    login(client)
    r=client.post('/api/tasks',json={'title':'Study Flask','priority':'high','category':'exam','due_date':'2030-01-01'}); assert r.status_code==201; task=r.get_json()['data']; tid=task['id']
    assert client.get('/api/tasks').status_code==200
    assert client.put(f'/api/tasks/{tid}',json={'completed':True}).status_code==200
    assert client.delete(f'/api/tasks/{tid}').status_code==200

def test_protected_task_api(client):
    assert client.get('/api/tasks').status_code==401

def test_task_page_and_copy_details(client,student):
    login(client)
    res = client.get('/tasks')
    assert res.status_code == 200
    assert b'tasks.js' in res.data
    js_res = client.get('/static/js/tasks.js')
    assert js_res.status_code == 200
    assert b'copyTaskDetails' in js_res.data
    assert b'Copy task details' in js_res.data

def test_overdue_task_indicators(client,student):
    login(client)
    # Add an overdue task
    r = client.post('/api/tasks', json={'title':'Overdue Report','priority':'high','category':'assignment','due_date':'2020-01-01'})
    assert r.status_code == 201
    # Check deadlines page renders overdue badge
    res = client.get('/deadlines')
    assert res.status_code == 200
    assert b'is-overdue' in res.data
    assert b'Overdue' in res.data
    # Check tasks js has overdue logic
    js_res = client.get('/static/js/tasks.js')
    assert js_res.status_code == 200
    assert b'isOverdue' in js_res.data
