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

def test_task_duplication(client,student,admin):
    login(client)
    r = client.post('/api/tasks', json={'title':'Project Presentation','priority':'high','category':'project','due_date':'2030-02-15'})
    assert r.status_code == 201
    tid = r.get_json()['data']['id']
    # Mark completed
    client.put(f'/api/tasks/{tid}', json={'completed':True})

    # Duplicate task
    dup_res = client.post(f'/api/tasks/{tid}/duplicate')
    assert dup_res.status_code == 201
    dup_data = dup_res.get_json()['data']
    assert dup_data['id'] != tid
    assert dup_data['title'] == 'Project Presentation (Copy)'
    assert dup_data['priority'] == 'high'
    assert dup_data['category'] == 'project'
    assert dup_data['due_date'] == '2030-02-15'
    assert dup_data['completed'] is False  # not completed!

    # 404 for bad task id
    assert client.post('/api/tasks/9999/duplicate').status_code == 404

    # Other user cannot duplicate
    client.post('/logout')
    login(client, 'admin@test.local')
    assert client.post(f'/api/tasks/{tid}/duplicate').status_code == 404

def test_bulk_complete_tasks(client,student,admin):
    login(client)
    r1 = client.post('/api/tasks', json={'title':'Task 1'})
    r2 = client.post('/api/tasks', json={'title':'Task 2'})
    id1, id2 = r1.get_json()['data']['id'], r2.get_json()['data']['id']

    # Bulk complete
    res = client.post('/api/tasks/bulk-complete', json={'ids':[id1, id2]})
    assert res.status_code == 200
    assert res.get_json()['data']['updated_count'] == 2

    # Verify both are completed
    tasks = client.get('/api/tasks').get_json()['data']
    task_map = {t['id']: t['completed'] for t in tasks}
    assert task_map[id1] is True
    assert task_map[id2] is True

    # Bad input
    assert client.post('/api/tasks/bulk-complete', json={'ids':'bad'}).status_code == 400
    assert client.post('/api/tasks/bulk-complete', json={'ids':[]}).status_code == 400

    # UI check
    page_res = client.get('/tasks')
    assert page_res.status_code == 200
    assert b'bulkCompleteBtn' in page_res.data
    assert b'selectAllTasks' in client.get('/static/js/tasks.js').data

