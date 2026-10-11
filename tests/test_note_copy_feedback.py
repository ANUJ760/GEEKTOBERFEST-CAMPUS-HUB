import pytest
from app.models import Note
from app.extensions import db

def test_notes_page_has_copy_button(client, student, app):
    with app.app_context():
        n = Note(user_id=student, title='Sample Lecture Note', subject='Physics', content='Quantum mechanics formulas.')
        db.session.add(n)
        db.session.commit()

    with client.session_transaction() as sess:
        sess['_user_id'] = str(student)
        sess['_fresh'] = True

    res = client.get('/notes')
    assert res.status_code == 200
    html = res.data.decode('utf-8')
    assert 'copyNoteText(' in html
    assert '>Copy<' in html
    assert 'Sample Lecture Note' in html

def test_notes_js_contains_copy_and_toast_feedback(client):
    res = client.get('/static/js/notes.js')
    assert res.status_code == 200
    js = res.data.decode('utf-8')
    assert 'copyNoteText' in js
    assert "toast('Note copied to clipboard')" in js
    assert "toast('Failed to copy note to clipboard','error')" in js
