from tests.conftest import login

def test_confirm_dialog_in_base_template(client, student):
    login(client)
    resp = client.get('/dashboard')
    assert resp.status_code == 200
    assert b'id="confirmModal"' in resp.data
    assert b'role="dialog"' in resp.data
    assert b'aria-modal="true"' in resp.data
    assert b'id="confirmModalConfirm"' in resp.data
    assert b'id="confirmModalCancel"' in resp.data

def test_admin_destructive_actions_have_confirm(client, admin, app):
    from app.models import Announcement, Resource
    from app.extensions import db
    with app.app_context():
        a = Announcement(title='Test Notice', content='Content', category='General', priority='Normal')
        r = Resource(title='Test Res', url='https://example.com')
        db.session.add_all([a, r])
        db.session.commit()

    login(client, 'admin@test.local')
    resp = client.get('/admin')
    assert resp.status_code == 200
    assert b'data-confirm="Are you sure you want to delete this announcement?"' in resp.data
    assert b'data-confirm="Are you sure you want to delete this resource?"' in resp.data

def test_notes_page_rendered_with_dialog(client, student):
    login(client)
    resp = client.get('/notes')
    assert resp.status_code == 200
    assert b'id="confirmModal"' in resp.data

def test_tasks_page_rendered_with_dialog(client, student):
    login(client)
    resp = client.get('/tasks')
    assert resp.status_code == 200
    assert b'id="confirmModal"' in resp.data
