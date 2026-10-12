from tests.conftest import login

def test_dashboard_stats(client,student):
    login(client);client.post('/api/tasks',json={'title':'One','completed':False});client.post('/api/tasks',json={'title':'Two'})
    data=client.get('/api/dashboard').get_json()['data'];assert data['total']==2;assert data['pending']==2;assert data['completed']==0;assert data['productivity']==0

def test_notification_relative_timestamps(client,student,app):
    from datetime import datetime, timedelta
    from app.extensions import db
    from app.models import Notification
    login(client)
    with app.app_context():
        n = Notification(user_id=student, title='Reminder', message='Check homework', created_at=datetime.now() - timedelta(hours=2))
        db.session.add(n)
        db.session.commit()
    res = client.get('/notifications')
    assert res.status_code == 200
    assert b'2 hours ago' in res.data
