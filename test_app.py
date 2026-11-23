from app import app, db
from models import Equipment, BookingRequest

def test_routes():
    client = app.test_client()

    routes = [
        ('/', 200),
        ('/equipment/1', 200),
        ('/book/1', 200),
        ('/requests', 200),
        ('/admin', 200),
        ('/analytics', 200),
        ('/ai-advisor', 200),
        ('/ai-advisor?q=yolo+drone+vision', 200)
    ]

    print("--- Running Route Verifications ---")
    for route, expected_status in routes:
        res = client.get(route)
        print(f"GET {route} -> Status: {res.status_code}")
        assert res.status_code == expected_status, f"Failed on {route}: got {res.status_code}"

    # Test Chat Advisor API
    print("--- Testing API Chat Advisor ---")
    api_res = client.post('/api/chat-advisor', json={'message': 'Need an oscilloscope for RF 2.4GHz'})
    print(f"POST /api/chat-advisor -> Status: {api_res.status_code}")
    assert api_res.status_code == 200
    json_data = api_res.get_json()
    print("Matched recommendations:", len(json_data.get('recommendations', [])))
    assert len(json_data.get('recommendations', [])) > 0

    print("ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    test_routes()
