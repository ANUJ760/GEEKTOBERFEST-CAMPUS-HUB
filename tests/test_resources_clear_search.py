import pytest
from app.models import Resource
from app.extensions import db

def test_resources_page_has_clear_search_button(client, student):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(student)
        sess['_fresh'] = True
    res = client.get('/resources')
    assert res.status_code == 200
    html = res.data.decode('utf-8')
    assert 'id="clearResourceSearch"' in html
    assert 'id="resourceSearch"' in html
    assert 'Clear' in html

def test_resources_api_search_and_clear(client, student, app):
    with app.app_context():
        r1 = Resource(title='Python Tutorial', description='Learn python basics', resource_type='Website', url='https://python.org', subject='CS')
        r2 = Resource(title='Calculus Textbook', description='Mathematics textbook', resource_type='PDF', url='https://math.org', subject='Math')
        db.session.add_all([r1, r2])
        db.session.commit()

    with client.session_transaction() as sess:
        sess['_user_id'] = str(student)
        sess['_fresh'] = True

    # Search for Python
    res = client.get('/api/resources?search=Python&type=all')
    assert res.status_code == 200
    items = res.get_json()['data']
    assert len(items) == 1
    assert items[0]['title'] == 'Python Tutorial'

    # Clear search (empty search param) restores full list
    res = client.get('/api/resources?search=&type=all')
    assert res.status_code == 200
    items = res.get_json()['data']
    assert len(items) == 2

    # Filter by type
    res = client.get('/api/resources?search=&type=PDF')
    assert res.status_code == 200
    items = res.get_json()['data']
    assert len(items) == 1
    assert items[0]['title'] == 'Calculus Textbook'
