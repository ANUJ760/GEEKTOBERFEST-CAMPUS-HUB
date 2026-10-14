from tests.conftest import login
from app.extensions import db
from app.models import User, StudyGroup, StudyGroupMember, StudyGroupResource


def create_user(app, name, email):
    with app.app_context():
        u = User(name=name, email=email, role='student')
        u.set_password('Password123')
        db.session.add(u)
        db.session.commit()
        return u.id


def test_create_study_group_api(client, student):
    login(client)
    res = client.post('/api/groups', json={
        'name': 'Algorithm Masters',
        'subject': 'Computer Science',
        'description': 'Solving dynamic programming together'
    })
    assert res.status_code == 201
    data = res.get_json()['data']
    assert data['name'] == 'Algorithm Masters'
    assert data['subject'] == 'Computer Science'
    assert data['member_count'] == 1
    assert data['is_member'] is True
    assert data['members'][0]['role'] == 'creator'


def test_list_and_filter_groups_api(client, app, student):
    login(client)
    user2_id = create_user(app, 'Student Two', 'student2@test.local')

    with app.app_context():
        g1 = StudyGroup(name='Math Study Club', subject='Math', creator_id=student)
        g2 = StudyGroup(name='History Buffs', subject='History', creator_id=user2_id)
        db.session.add_all([g1, g2])
        db.session.flush()
        db.session.add(StudyGroupMember(group_id=g1.id, user_id=student, role='creator'))
        db.session.add(StudyGroupMember(group_id=g2.id, user_id=user2_id, role='creator'))
        db.session.commit()

    # List all
    res = client.get('/api/groups')
    assert res.status_code == 200
    assert len(res.get_json()['data']) == 2

    # Filter mine
    res = client.get('/api/groups?mine=true')
    assert res.status_code == 200
    data = res.get_json()['data']
    assert len(data) == 1
    assert data[0]['name'] == 'Math Study Club'

    # Filter by search
    res = client.get('/api/groups?search=history')
    assert res.status_code == 200
    data = res.get_json()['data']
    assert len(data) == 1
    assert data[0]['name'] == 'History Buffs'


def test_group_join_and_leave(client, app, student):
    user2_id = create_user(app, 'Peer User', 'peer@test.local')
    with app.app_context():
        group = StudyGroup(name='Physics Group', subject='Physics', creator_id=user2_id)
        db.session.add(group)
        db.session.flush()
        db.session.add(StudyGroupMember(group_id=group.id, user_id=user2_id, role='creator'))
        db.session.commit()
        group_id = group.id

    login(client)
    # Join
    res = client.post(f'/api/groups/{group_id}/join')
    assert res.status_code == 200

    # Duplicate join fails
    res = client.post(f'/api/groups/{group_id}/join')
    assert res.status_code == 400

    # Leave
    res = client.post(f'/api/groups/{group_id}/leave')
    assert res.status_code == 200

    # Leaving when not a member fails
    res = client.post(f'/api/groups/{group_id}/leave')
    assert res.status_code == 400


def test_shared_resources_authorization(client, app, student):
    user2_id = create_user(app, 'Owner User', 'owner@test.local')
    user3_id = create_user(app, 'Other Member', 'other@test.local')

    with app.app_context():
        g = StudyGroup(name='Biology Circle', subject='Biology', creator_id=user2_id)
        db.session.add(g)
        db.session.flush()
        db.session.add(StudyGroupMember(group_id=g.id, user_id=user2_id, role='creator'))
        db.session.add(StudyGroupMember(group_id=g.id, user_id=user3_id, role='member'))
        db.session.commit()
        group_id = g.id

    login(client)  # logged in as `student` (who is NOT a member yet)

    # Non-member cannot view shared resources
    res = client.get(f'/api/groups/{group_id}/resources')
    assert res.status_code == 403

    # Non-member cannot add shared resource
    res = client.post(f'/api/groups/{group_id}/resources', json={
        'title': 'Cell Biology Slides',
        'url': 'https://example.com/slides'
    })
    assert res.status_code == 403

    # Join the group
    client.post(f'/api/groups/{group_id}/join')

    # Now as a member, can add shared resource
    res = client.post(f'/api/groups/{group_id}/resources', json={
        'title': 'Cell Biology Slides',
        'url': 'https://example.com/slides',
        'resource_type': 'PDF'
    })
    assert res.status_code == 201
    resource_id = res.get_json()['data']['id']

    # Now can view shared resources
    res = client.get(f'/api/groups/{group_id}/resources')
    assert res.status_code == 200
    assert len(res.get_json()['data']) == 1

    # Log in as user3 (another member, not the author and not the group creator)
    client.post('/logout')
    login(client, email='other@test.local')
    res = client.delete(f'/api/groups/{group_id}/resources/{resource_id}')
    assert res.status_code == 403  # Cannot delete someone else's resource!

    # Log in as user2 (group creator)
    client.post('/logout')
    login(client, email='owner@test.local')
    res = client.delete(f'/api/groups/{group_id}/resources/{resource_id}')
    assert res.status_code == 200  # Group creator can delete resources


def test_delete_group_authorization(client, app, student):
    user2_id = create_user(app, 'Creator User', 'creator@test.local')
    with app.app_context():
        g = StudyGroup(name='Chemistry Club', subject='Chemistry', creator_id=user2_id)
        db.session.add(g)
        db.session.flush()
        db.session.add(StudyGroupMember(group_id=g.id, user_id=user2_id, role='creator'))
        db.session.add(StudyGroupMember(group_id=g.id, user_id=student, role='member'))
        db.session.commit()
        group_id = g.id

    login(client)  # logged in as `student` (member, but not creator)
    res = client.delete(f'/api/groups/{group_id}')
    assert res.status_code == 403

    # Creator can delete
    client.post('/logout')
    login(client, email='creator@test.local')
    res = client.delete(f'/api/groups/{group_id}')
    assert res.status_code == 200


def test_web_groups_flow(client, student):
    login(client)
    # Create group via web
    res = client.post('/groups', data={
        'name': 'Calculus Team',
        'subject': 'Mathematics',
        'description': 'Integration and differentiation practice'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b'Calculus Team' in res.data
    assert b'Study group created successfully' in res.data

    # View groups index
    res = client.get('/groups')
    assert res.status_code == 200
    assert b'Calculus Team' in res.data
