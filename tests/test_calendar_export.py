from datetime import date
from tests.conftest import login
from app.models import Task
from app.extensions import db

def test_calendar_export_route(client, student, app):
    with app.app_context():
        t1 = Task(user_id=student, title='Math Exam', description='Calculus chapter 1-4', priority='high', category='exam', due_date=date(2026, 11, 15), completed=False)
        t2 = Task(user_id=student, title='No Due Date Task', completed=False)
        t3 = Task(user_id=student, title='Completed Assignment', category='assignment', due_date=date(2026, 11, 10), completed=True)
        db.session.add_all([t1, t2, t3])
        db.session.commit()

    # Unauthenticated
    resp = client.get('/deadlines/export.ics')
    assert resp.status_code == 302

    # Authenticated
    login(client)
    resp = client.get('/deadlines/export.ics')
    assert resp.status_code == 200
    assert 'text/calendar' in resp.content_type
    assert 'attachment' in resp.headers.get('Content-Disposition', '')
    content = resp.data.decode('utf-8')

    assert 'BEGIN:VCALENDAR' in content
    assert 'VERSION:2.0' in content
    assert 'END:VCALENDAR' in content

    # Should include t1
    assert 'SUMMARY:Math Exam' in content
    assert 'DTSTART;VALUE=DATE:20261115' in content
    assert 'DTEND;VALUE=DATE:20261116' in content
    assert 'STATUS:NEEDS-ACTION' in content
    assert 'PRIORITY:1' in content

    # Should include t3
    assert 'SUMMARY:Completed Assignment' in content
    assert 'STATUS:COMPLETED' in content

    # Should NOT include t2 (no due date)
    assert 'No Due Date Task' not in content

def test_calendar_export_api(client, student, app):
    with app.app_context():
        t1 = Task(user_id=student, title='Pending API Task', due_date=date(2026, 12, 1), completed=False)
        t2 = Task(user_id=student, title='Done API Task', due_date=date(2026, 12, 5), completed=True)
        db.session.add_all([t1, t2])
        db.session.commit()

    # Unauthenticated
    resp = client.get('/api/tasks/calendar.ics')
    assert resp.status_code == 401

    login(client)
    # Filter pending
    resp = client.get('/api/tasks/calendar.ics?status=pending')
    assert resp.status_code == 200
    content = resp.data.decode('utf-8')
    assert 'Pending API Task' in content
    assert 'Done API Task' not in content

def test_calendar_export_user_scoping(client, student, admin, app):
    with app.app_context():
        t_student = Task(user_id=student, title='Student Private Task', due_date=date(2026, 12, 10))
        t_admin = Task(user_id=admin, title='Admin Private Task', due_date=date(2026, 12, 12))
        db.session.add_all([t_student, t_admin])
        db.session.commit()

    login(client, 'student@test.local')
    resp = client.get('/deadlines/export.ics')
    content = resp.data.decode('utf-8')
    assert 'Student Private Task' in content
    assert 'Admin Private Task' not in content

def test_deadlines_page_has_calendar_button(client, student):
    login(client)
    resp = client.get('/deadlines')
    assert resp.status_code == 200
    assert b'Export iCalendar (.ics)' in resp.data
