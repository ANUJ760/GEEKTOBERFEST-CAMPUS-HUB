from tests.conftest import login

def test_register(client):
    r=client.post('/register',data={'name':'New User','email':'new@test.local','password':'Password123'},follow_redirects=True); assert r.status_code==200; assert b'Welcome back' in r.data

def test_invalid_login(client):
    r=client.post('/login',data={'email':'bad@test.local','password':'wrong'}); assert r.status_code==200; assert b'Invalid email or password' in r.data

def test_logout(client,student):
    login(client); r=client.post('/logout',follow_redirects=True); assert r.status_code==200; assert b'logged out' in r.data

def test_password_visibility_toggle(client):
    r_login = client.get('/login')
    assert r_login.status_code == 200
    assert b'pw-toggle-btn' in r_login.data
    assert b'aria-label="Show password"' in r_login.data
    assert b'togglePasswordVisibility' in r_login.data

    r_reg = client.get('/register')
    assert r_reg.status_code == 200
    assert b'pw-toggle-btn' in r_reg.data
    assert b'togglePasswordVisibility' in r_reg.data
