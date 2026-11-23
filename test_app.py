from app import app, db
from models import User

def test_routes():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()

    print("--- 1. Testing Public Routes ---")
    public_routes = [
        ('/', 200),
        ('/equipment/1', 200),
        ('/analytics', 200),
        ('/ai-advisor', 200),
        ('/login', 200),
        ('/register', 200),
        ('/ai-advisor?q=yolo+drone+vision', 200)
    ]
    for route, expected_status in public_routes:
        res = client.get(route)
        print(f"GET {route} -> Status: {res.status_code}")
        assert res.status_code == expected_status, f"Failed on {route}: got {res.status_code}"

    print("--- 2. Testing Unauthenticated Route Protection (Redirects to /login) ---")
    protected_routes = ['/book/1', '/requests', '/admin', '/admin/manage-equipment']
    for route in protected_routes:
        res = client.get(route)
        print(f"GET {route} (unauthenticated) -> Status: {res.status_code}")
        assert res.status_code == 302, f"Security failure on {route}: expected 302 redirect, got {res.status_code}"

    print("--- 3. Testing Authenticated Student Access ---")
    # Log in as demo student
    client.post('/login', data={'login_id': 'priya.r', 'password': 'StudentPassword2026!'}, follow_redirects=True)
    res_book = client.get('/book/1')
    print(f"GET /book/1 (student authenticated) -> Status: {res_book.status_code}")
    assert res_book.status_code == 200

    res_req = client.get('/requests')
    print(f"GET /requests (student authenticated) -> Status: {res_req.status_code}")
    assert res_req.status_code == 200

    # Student accessing admin must receive 403 Forbidden
    res_admin_forbidden = client.get('/admin')
    print(f"GET /admin (student authenticated) -> Status: {res_admin_forbidden.status_code}")
    assert res_admin_forbidden.status_code == 403

    client.get('/logout')

    print("--- 4. Testing Authenticated Faculty Access ---")
    # Log in as demo faculty
    client.post('/login', data={'login_id': 'arvind.cse', 'password': 'FacultyPassword2026!'}, follow_redirects=True)
    res_admin = client.get('/admin')
    print(f"GET /admin (faculty authenticated) -> Status: {res_admin.status_code}")
    assert res_admin.status_code == 200
    client.get('/logout')

    print("--- 5. Testing API Chat Advisor ---")
    api_res = client.post('/api/chat-advisor', json={'message': 'Need an oscilloscope for RF 2.4GHz'})
    print(f"POST /api/chat-advisor -> Status: {api_res.status_code}")
    assert api_res.status_code == 200
    json_data = api_res.get_json()
    print("Matched recommendations:", len(json_data.get('recommendations', [])))
    assert len(json_data.get('recommendations', [])) > 0

    print("ALL ROUTE & SECURITY VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    test_routes()
