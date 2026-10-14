from datetime import time
from tests.conftest import login
from app.extensions import db
from app.models import User, TimetableEntry


def create_user(app, name, email):
    with app.app_context():
        u = User(name=name, email=email, role='student')
        u.set_password('Password123')
        db.session.add(u)
        db.session.commit()
        return u.id


def test_create_timetable_entry_api(client, student):
    login(client)
    res = client.post('/api/timetable', json={
        'course_code': 'CS101',
        'course_name': 'Introduction to Computer Science',
        'day_of_week': 0,
        'start_time': '09:00',
        'end_time': '10:30',
        'location': 'Room 101',
        'instructor': 'Prof. Knuth',
        'color': '#3157d5'
    })
    assert res.status_code == 201
    data = res.get_json()['data']
    assert data['course_code'] == 'CS101'
    assert data['course_name'] == 'Introduction to Computer Science'
    assert data['day_of_week'] == 0
    assert data['day_name'] == 'Monday'
    assert data['start_time'] == '09:00'
    assert data['end_time'] == '10:30'
    assert data['location'] == 'Room 101'


def test_timetable_validation(client, student):
    login(client)

    # Invalid day_of_week
    res = client.post('/api/timetable', json={
        'course_code': 'CS101',
        'course_name': 'CS',
        'day_of_week': 7,
        'start_time': '09:00',
        'end_time': '10:00'
    })
    assert res.status_code == 400

    # Start time after end time
    res = client.post('/api/timetable', json={
        'course_code': 'CS101',
        'course_name': 'CS',
        'day_of_week': 1,
        'start_time': '11:00',
        'end_time': '10:00'
    })
    assert res.status_code == 400

    # Invalid time format
    res = client.post('/api/timetable', json={
        'course_code': 'CS101',
        'course_name': 'CS',
        'day_of_week': 1,
        'start_time': 'invalid',
        'end_time': '10:00'
    })
    assert res.status_code == 400


def test_get_and_filter_timetable(client, app, student):
    login(client)
    user2_id = create_user(app, 'Other Student', 'other@test.local')

    with app.app_context():
        e1 = TimetableEntry(user_id=student, course_code='MATH101', course_name='Calculus', day_of_week=0, start_time=time(9, 0), end_time=time(10, 0))
        e2 = TimetableEntry(user_id=student, course_code='PHYS101', course_name='Physics', day_of_week=2, start_time=time(14, 0), end_time=time(15, 30))
        # Another user's entry
        e_other = TimetableEntry(user_id=user2_id, course_code='CHEM101', course_name='Chemistry', day_of_week=0, start_time=time(9, 0), end_time=time(10, 0))
        db.session.add_all([e1, e2, e_other])
        db.session.commit()

    # Get all entries for current_user
    res = client.get('/api/timetable')
    assert res.status_code == 200
    data = res.get_json()['data']
    assert len(data) == 2
    codes = [e['course_code'] for e in data]
    assert 'MATH101' in codes
    assert 'PHYS101' in codes
    assert 'CHEM101' not in codes

    # Filter by day
    res = client.get('/api/timetable?day=0')
    assert res.status_code == 200
    data = res.get_json()['data']
    assert len(data) == 1
    assert data[0]['course_code'] == 'MATH101'


def test_update_and_delete_entry(client, app, student):
    user2_id = create_user(app, 'Another User', 'another@test.local')

    with app.app_context():
        e = TimetableEntry(user_id=student, course_code='BIO101', course_name='Biology', day_of_week=3, start_time=time(10, 0), end_time=time(11, 0))
        e_other = TimetableEntry(user_id=user2_id, course_code='ENG101', course_name='English', day_of_week=3, start_time=time(10, 0), end_time=time(11, 0))
        db.session.add_all([e, e_other])
        db.session.commit()
        entry_id = e.id
        other_entry_id = e_other.id

    login(client)

    # Update own entry
    res = client.put(f'/api/timetable/{entry_id}', json={
        'course_name': 'Advanced Biology',
        'location': 'Lab 2'
    })
    assert res.status_code == 200
    assert res.get_json()['data']['course_name'] == 'Advanced Biology'
    assert res.get_json()['data']['location'] == 'Lab 2'

    # Cannot update other user's entry (404 scoped)
    res = client.put(f'/api/timetable/{other_entry_id}', json={'course_name': 'Hacked'})
    assert res.status_code == 404

    # Cannot delete other user's entry
    res = client.delete(f'/api/timetable/{other_entry_id}')
    assert res.status_code == 404

    # Can delete own entry
    res = client.delete(f'/api/timetable/{entry_id}')
    assert res.status_code == 200


def test_upcoming_classes_api(client, app, student):
    login(client)
    with app.app_context():
        e = TimetableEntry(user_id=student, course_code='CS201', course_name='OS', day_of_week=0, start_time=time(8, 0), end_time=time(10, 0))
        db.session.add(e)
        db.session.commit()

    res = client.get('/api/timetable/upcoming')
    assert res.status_code == 200
    data = res.get_json()['data']
    assert len(data) >= 1
    assert data[0]['course_code'] == 'CS201'


def test_timetable_web_routes(client, student):
    login(client)

    # Add class via web form
    res = client.post('/timetable', data={
        'course_code': 'MATH202',
        'course_name': 'Linear Algebra',
        'day_of_week': '2',
        'start_time': '13:00',
        'end_time': '14:30',
        'location': 'Hall C',
        'instructor': 'Prof. Strang',
        'color': '#3157d5'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b'Added MATH202 to timetable' in res.data
    assert b'Linear Algebra' in res.data

    # Timetable page renders
    res = client.get('/timetable')
    assert res.status_code == 200
    assert b'Weekly academic schedule' in res.data
    assert b'MATH202' in res.data
