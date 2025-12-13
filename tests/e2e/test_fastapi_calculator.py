from datetime import datetime, timezone
from uuid import uuid4
import pytest
import requests

# Import the Calculation model for direct model tests.
from app.models.calculation import Calculation

# ---------------------------------------------------------------------------
# Helper Fixtures and Functions
# ---------------------------------------------------------------------------
@pytest.fixture
def base_url(fastapi_server: str) -> str:
    """
    Returns the FastAPI server base URL without a trailing slash.
    """
    return fastapi_server.rstrip("/")

def _parse_datetime(dt_str: str) -> datetime:
    """Helper function to parse datetime strings from API responses."""
    if dt_str.endswith('Z'):
        dt_str = dt_str.replace('Z', '+00:00')
    return datetime.fromisoformat(dt_str)

def register_and_login(base_url: str, user_data: dict) -> dict:
    """
    Registers a new user and logs in, returning the token response data.
    """
    reg_url = f"{base_url}/auth/register"
    login_url = f"{base_url}/auth/login"
    
    reg_response = requests.post(reg_url, json=user_data)
    assert reg_response.status_code == 201, f"User registration failed: {reg_response.text}"
    
    login_payload = {
        "username": user_data["username"],
        "password": user_data["password"]
    }
    login_response = requests.post(login_url, json=login_payload)
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    return login_response.json()

# ---------------------------------------------------------------------------
# Health and Auth Endpoint Tests
# ---------------------------------------------------------------------------
def test_health_endpoint(base_url: str):
    url = f"{base_url}/health"
    response = requests.get(url)
    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}. Response: {response.text}"
    assert response.json() == {"status": "ok"}, "Unexpected response from /health."

def test_user_registration(base_url: str):
    url = f"{base_url}/auth/register"
    payload = {
        "first_name": "Alice",
        "last_name": "Smith",
        "email": "alice.smith@example.com",
        "username": "alicesmith",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!"
    }
    response = requests.post(url, json=payload)
    assert response.status_code == 201, f"Expected 201 but got {response.status_code}. Response: {response.text}"
    data = response.json()
    for key in ["id", "username", "email", "first_name", "last_name", "is_active", "is_verified"]:
        assert key in data, f"Field '{key}' missing in registration response."
    assert data["username"] == "alicesmith"
    assert data["email"] == "alice.smith@example.com"
    assert data["first_name"] == "Alice"
    assert data["last_name"] == "Smith"
    assert data["is_active"] is True
    assert data["is_verified"] is False

def test_user_login(base_url: str):
    reg_url = f"{base_url}/auth/register"
    login_url = f"{base_url}/auth/login"
    
    test_user = {
        "first_name": "Bob",
        "last_name": "Jones",
        "email": "bob.jones@example.com",
        "username": "bobjones",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!"
    }
    
    # Register user
    reg_response = requests.post(reg_url, json=test_user)
    assert reg_response.status_code == 201, f"User registration failed: {reg_response.text}"
    
    # Login user
    login_payload = {
        "username": test_user["username"],
        "password": test_user["password"]
    }
    login_response = requests.post(login_url, json=login_payload)
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    
    login_data = login_response.json()
    required_fields = {
        "access_token": str,
        "refresh_token": str,
        "token_type": str,
        "expires_at": str,  # ISO datetime string
        "user_id": str,     # UUID string
        "username": str,
        "email": str,
        "first_name": str,
        "last_name": str,
        "is_active": bool,
        "is_verified": bool
    }
    
    for field, expected_type in required_fields.items():
        assert field in login_data, f"Missing field: {field}"
        assert isinstance(login_data[field], expected_type), f"Field {field} has wrong type. Expected {expected_type}, got {type(login_data[field])}"
    
    assert login_data["token_type"].lower() == "bearer", "Token type should be 'bearer'"
    assert len(login_data["access_token"]) > 0, "Access token should not be empty"
    assert len(login_data["refresh_token"]) > 0, "Refresh token should not be empty"
    assert login_data["username"] == test_user["username"]
    assert login_data["email"] == test_user["email"]
    assert login_data["first_name"] == test_user["first_name"]
    assert login_data["last_name"] == test_user["last_name"]
    assert login_data["is_active"] is True
    
    expires_at = _parse_datetime(login_data["expires_at"])
    current_time = datetime.now(timezone.utc)
    assert expires_at.tzinfo is not None, "expires_at should be timezone-aware"
    assert current_time.tzinfo is not None, "current_time should be timezone-aware"
    assert expires_at > current_time, "Token expiration should be in the future"

# ---------------------------------------------------------------------------
# Calculations Endpoints Integration Tests
# ---------------------------------------------------------------------------
# Note: All calculation creation requests now use the /calculations endpoint (not /calculations/add)
def test_create_calculation_addition(base_url: str):
    user_data = {
        "first_name": "Calc",
        "last_name": "Adder",
        "email": f"calc.adder{uuid4()}@example.com",
        "username": f"calc_adder_{uuid4()}",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!"
    }
    token_data = register_and_login(base_url, user_data)
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"{base_url}/calculations"
    payload = {
        "type": "addition",
        "inputs": [10.5, 3, 2],
        "user_id": "ignored"
    }
    response = requests.post(url, json=payload, headers=headers)
    assert response.status_code == 201, f"Addition calculation creation failed: {response.text}"
    data = response.json()
    assert "result" in data and data["result"] == 15.5, f"Expected result 15.5, got {data.get('result')}"

def test_create_calculation_subtraction(base_url: str):
    user_data = {
        "first_name": "Calc",
        "last_name": "Subtractor",
        "email": f"calc.sub{uuid4()}@example.com",
        "username": f"calc_sub_{uuid4()}",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!"
    }
    token_data = register_and_login(base_url, user_data)
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"{base_url}/calculations"
    payload = {
        "type": "subtraction",
        "inputs": [10, 3, 2],
        "user_id": "ignored"
    }
    response = requests.post(url, json=payload, headers=headers)
    assert response.status_code == 201, f"Subtraction calculation creation failed: {response.text}"
    data = response.json()
    # Expected result: 10 - 3 - 2 = 5
    assert "result" in data and data["result"] == 5, f"Expected result 5, got {data.get('result')}"

def test_create_calculation_multiplication(base_url: str):
    user_data = {
        "first_name": "Calc",
        "last_name": "Multiplier",
        "email": f"calc.mult{uuid4()}@example.com",
        "username": f"calc_mult_{uuid4()}",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!"
    }
    token_data = register_and_login(base_url, user_data)
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"{base_url}/calculations"
    payload = {
        "type": "multiplication",
        "inputs": [2, 3, 4],
        "user_id": "ignored"
    }
    response = requests.post(url, json=payload, headers=headers)
    assert response.status_code == 201, f"Multiplication calculation creation failed: {response.text}"
    data = response.json()
    # Expected result: 2 * 3 * 4 = 24
    assert "result" in data and data["result"] == 24, f"Expected result 24, got {data.get('result')}"

def test_create_calculation_division(base_url: str):
    user_data = {
        "first_name": "Calc",
        "last_name": "Divider",
        "email": f"calc.div{uuid4()}@example.com",
        "username": f"calc_div_{uuid4()}",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!"
    }
    token_data = register_and_login(base_url, user_data)
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"{base_url}/calculations"
    payload = {
        "type": "division",
        "inputs": [100, 2, 5],
        "user_id": "ignored"
    }
    response = requests.post(url, json=payload, headers=headers)
    assert response.status_code == 201, f"Division calculation creation failed: {response.text}"
    data = response.json()
    # Expected result: 100 / 2 / 5 = 10
    assert "result" in data and data["result"] == 10, f"Expected result 10, got {data.get('result')}"

def test_list_get_update_delete_calculation(base_url: str):
    user_data = {
        "first_name": "Calc",
        "last_name": "CRUD",
        "email": f"calc.crud{uuid4()}@example.com",
        "username": f"calc_crud_{uuid4()}",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!"
    }
    token_data = register_and_login(base_url, user_data)
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Create a calculation (e.g., multiplication)
    create_url = f"{base_url}/calculations"
    payload = {
        "type": "multiplication",
        "inputs": [3, 4],
        "user_id": "ignored"
    }
    create_response = requests.post(create_url, json=payload, headers=headers)
    assert create_response.status_code == 201, f"Calculation creation failed: {create_response.text}"
    calc = create_response.json()
    calc_id = calc["id"]
    
    # List calculations
    list_url = f"{base_url}/calculations"
    list_response = requests.get(list_url, headers=headers)
    assert list_response.status_code == 200, f"List calculations failed: {list_response.text}"
    calc_list = list_response.json()
    assert any(c["id"] == calc_id for c in calc_list), "Created calculation not found in list"
    
    # Get calculation by ID
    get_url = f"{base_url}/calculations/{calc_id}"
    get_response = requests.get(get_url, headers=headers)
    assert get_response.status_code == 200, f"Get calculation failed: {get_response.text}"
    get_calc = get_response.json()
    assert get_calc["id"] == calc_id, "Mismatch in calculation id"
    
    # Update calculation: change inputs (e.g., from [3,4] to [5,6])
    update_url = f"{base_url}/calculations/{calc_id}"
    update_payload = {"inputs": [5, 6]}
    update_response = requests.put(update_url, json=update_payload, headers=headers)
    assert update_response.status_code == 200, f"Update calculation failed: {update_response.text}"
    updated_calc = update_response.json()
    # For multiplication, expected result = 5 * 6 = 30
    expected_result = 30
    assert updated_calc["result"] == expected_result, f"Expected updated result {expected_result}, got {updated_calc['result']}"
    
    # Delete calculation
    delete_url = f"{base_url}/calculations/{calc_id}"
    delete_response = requests.delete(delete_url, headers=headers)
    assert delete_response.status_code == 204, f"Delete calculation failed: {delete_response.text}"
    
    # Verify deletion: GET should return 404
    get_response_after_delete = requests.get(get_url, headers=headers)
    assert get_response_after_delete.status_code == 404, "Expected 404 after deletion"

# ---------------------------------------------------------------------------
# Direct Model Tests for Calculation Operations
# ---------------------------------------------------------------------------
def test_model_addition():
    dummy_user_id = uuid4()
    calc = Calculation.create("addition", dummy_user_id, [1, 2, 3])
    result = calc.get_result()
    assert result == 6, f"Addition result incorrect: expected 6, got {result}"

def test_password_update_successful(base_url: str):
    """Test successful password update via API"""
    user_data = {
        "first_name": "Password",
        "last_name": "Tester",
        "email": f"password.tester{uuid4()}@example.com",
        "username": f"pt_{uuid4().hex[:8]}",
        "password": "OldPass123!",
        "confirm_password": "OldPass123!"
    }
    
    # Register and login
    token_data = register_and_login(base_url, user_data)
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Update password
    password_update_url = f"{base_url}/users/password"
    password_update_payload = {
        "current_password": "OldPass123!",
        "new_password": "NewPass456!",
        "confirm_new_password": "NewPass456!"
    }
    
    update_response = requests.put(password_update_url, json=password_update_payload, headers=headers)
    assert update_response.status_code == 200, f"Password update failed: {update_response.text}"
    
    update_data = update_response.json()
    assert "message" in update_data, "Response should contain message"
    assert "logout_required" in update_data, "Response should indicate logout required"
    assert update_data["logout_required"] is True, "logout_required should be True"
    
    # Verify old password no longer works by attempting login
    login_url = f"{base_url}/auth/login"
    old_login_payload = {
        "username": user_data["username"],
        "password": "OldPass123!"
    }
    old_login_response = requests.post(login_url, json=old_login_payload)
    assert old_login_response.status_code == 401, "Old password should not work after update"
    
    # Verify new password works
    new_login_payload = {
        "username": user_data["username"],
        "password": "NewPass456!"
    }
    new_login_response = requests.post(login_url, json=new_login_payload)
    assert new_login_response.status_code == 200, "New password should work after update"
    new_token_data = new_login_response.json()
    assert "access_token" in new_token_data, "Should receive access token with new password"

def test_password_update_incorrect_current_password(base_url: str):
    """Test password update fails with incorrect current password"""
    user_data = {
        "first_name": "Password",
        "last_name": "Tester",
        "email": f"password.tester2{uuid4()}@example.com",
        "username": f"pt_{uuid4().hex[:8]}",
        "password": "OldPass123!",
        "confirm_password": "OldPass123!"
    }
    
    token_data = register_and_login(base_url, user_data)
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    password_update_url = f"{base_url}/users/password"
    password_update_payload = {
        "current_password": "WrongPass123!",  # Incorrect current password
        "new_password": "NewPass456!",
        "confirm_new_password": "NewPass456!"
    }
    
    update_response = requests.put(password_update_url, json=password_update_payload, headers=headers)
    assert update_response.status_code == 400, "Should return 400 for incorrect current password"
    
    error_data = update_response.json()
    assert "detail" in error_data, "Error response should contain detail"
    assert "incorrect" in error_data["detail"].lower(), "Error should mention incorrect password"

def test_password_update_password_mismatch(base_url: str):
    """Test password update fails when new password and confirmation don't match"""
    user_data = {
        "first_name": "Password",
        "last_name": "Tester",
        "email": f"password.tester3{uuid4()}@example.com",
        "username": f"pt_{uuid4().hex[:8]}",
        "password": "OldPass123!",
        "confirm_password": "OldPass123!"
    }
    
    token_data = register_and_login(base_url, user_data)
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    password_update_url = f"{base_url}/users/password"
    password_update_payload = {
        "current_password": "OldPass123!",
        "new_password": "NewPass456!",
        "confirm_new_password": "DifferentPass789!"  # Mismatch
    }
    
    update_response = requests.put(password_update_url, json=password_update_payload, headers=headers)
    assert update_response.status_code == 422, "Should return 422 for validation error"
    
    error_data = update_response.json()
    assert "detail" in error_data, "Error response should contain detail"

def test_password_update_same_as_current(base_url: str):
    """Test password update fails when new password is same as current"""
    user_data = {
        "first_name": "Password",
        "last_name": "Tester",
        "email": f"password.tester4{uuid4()}@example.com",
        "username": f"pt_{uuid4().hex[:8]}",
        "password": "OldPass123!",
        "confirm_password": "OldPass123!"
    }
    
    token_data = register_and_login(base_url, user_data)
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    password_update_url = f"{base_url}/users/password"
    password_update_payload = {
        "current_password": "OldPass123!",
        "new_password": "OldPass123!",  # Same as current
        "confirm_new_password": "OldPass123!"
    }
    
    update_response = requests.put(password_update_url, json=password_update_payload, headers=headers)
    assert update_response.status_code == 422, "Should return 422 for validation error"
    
    error_data = update_response.json()
    assert "detail" in error_data, "Error response should contain detail"

def test_password_update_weak_password(base_url: str):
    """Test password update fails with weak password (missing requirements)"""
    user_data = {
        "first_name": "Password",
        "last_name": "Tester",
        "email": f"password.tester5{uuid4()}@example.com",
        "username": f"pt_{uuid4().hex[:8]}",
        "password": "OldPass123!",
        "confirm_password": "OldPass123!"
    }
    
    token_data = register_and_login(base_url, user_data)
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    password_update_url = f"{base_url}/users/password"
    
    # Test password without uppercase
    password_update_payload = {
        "current_password": "OldPass123!",
        "new_password": "newpass123!",
        "confirm_new_password": "newpass123!"
    }
    update_response = requests.put(password_update_url, json=password_update_payload, headers=headers)
    assert update_response.status_code == 422, "Should return 422 for weak password"
    
    # Test password without special character
    password_update_payload = {
        "current_password": "OldPass123!",
        "new_password": "NewPass123",
        "confirm_new_password": "NewPass123"
    }
    update_response = requests.put(password_update_url, json=password_update_payload, headers=headers)
    assert update_response.status_code == 422, "Should return 422 for password without special character"

def test_password_update_unauthorized(base_url: str):
    """Test password update fails without authentication"""
    password_update_url = f"{base_url}/users/password"
    password_update_payload = {
        "current_password": "OldPass123!",
        "new_password": "NewPass456!",
        "confirm_new_password": "NewPass456!"
    }
    
    # Try without authorization header
    update_response = requests.put(password_update_url, json=password_update_payload)
    assert update_response.status_code == 401, "Should return 401 without authentication"
    
    # Try with invalid token
    invalid_headers = {"Authorization": "Bearer invalid_token_here"}
    update_response = requests.put(password_update_url, json=password_update_payload, headers=invalid_headers)
    assert update_response.status_code == 401, "Should return 401 with invalid token"

# ---------------------------------------------------------------------------
# Profile Picture Update Tests
# ---------------------------------------------------------------------------
def test_upload_profile_picture_successful(base_url: str):
    """Test successful profile picture upload"""
    import io
    from PIL import Image
    
    user_data = {
        "first_name": "Profile",
        "last_name": "Picture",
        "email": f"profile.pic{uuid4()}@example.com",
        "username": f"pp_{uuid4().hex[:8]}",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!"
    }
    
    token_data = register_and_login(base_url, user_data)
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    # Upload profile picture
    upload_url = f"{base_url}/users/profile-picture"
    files = {"file": ("test_image.png", img_bytes, "image/png")}
    
    upload_response = requests.post(upload_url, files=files, headers=headers)
    assert upload_response.status_code == 200, f"Profile picture upload failed: {upload_response.text}"
    
    user_data_response = upload_response.json()
    assert "profile_picture" in user_data_response, "Response should contain profile_picture"
    assert user_data_response["profile_picture"] is not None, "Profile picture path should be set"
    assert user_data_response["profile_picture"].startswith("/static/uploads/profile_pictures/"), \
        "Profile picture path should be in correct location"
    assert "user_" in user_data_response["profile_picture"], "Filename should contain user ID"
    assert user_data_response["profile_picture"].endswith(".png"), "File extension should be preserved"
    
    # Verify user profile was updated
    profile_url = f"{base_url}/users/me"
    profile_response = requests.get(profile_url, headers=headers)
    assert profile_response.status_code == 200
    profile_data = profile_response.json()
    assert profile_data["profile_picture"] == user_data_response["profile_picture"], \
        "Profile picture should be persisted"

def test_upload_profile_picture_invalid_file_type(base_url: str):
    """Test profile picture upload fails with invalid file type"""
    import io
    
    user_data = {
        "first_name": "Profile",
        "last_name": "Picture",
        "email": f"profile.pic2{uuid4()}@example.com",
        "username": f"pp_{uuid4().hex[:8]}",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!"
    }
    
    token_data = register_and_login(base_url, user_data)
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Try to upload a text file (invalid)
    upload_url = f"{base_url}/users/profile-picture"
    files = {"file": ("test.txt", io.BytesIO(b"Not an image"), "text/plain")}
    
    upload_response = requests.post(upload_url, files=files, headers=headers)
    assert upload_response.status_code == 400, "Should return 400 for invalid file type"
    
    error_data = upload_response.json()
    assert "detail" in error_data, "Error response should contain detail"
    assert "invalid" in error_data["detail"].lower() or "file type" in error_data["detail"].lower(), \
        "Error should mention invalid file type"

def test_upload_profile_picture_file_too_large(base_url: str):
    """Test profile picture upload fails with file exceeding size limit"""
    import io
    
    user_data = {
        "first_name": "Profile",
        "last_name": "Picture",
        "email": f"profile.pic3{uuid4()}@example.com",
        "username": f"pp_{uuid4().hex[:8]}",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!"
    }
    
    token_data = register_and_login(base_url, user_data)
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Create a file larger than 5MB
    large_file_content = b"x" * (6 * 1024 * 1024)  # 6MB
    upload_url = f"{base_url}/users/profile-picture"
    files = {"file": ("large_image.png", io.BytesIO(large_file_content), "image/png")}
    
    upload_response = requests.post(upload_url, files=files, headers=headers)
    assert upload_response.status_code == 400, "Should return 400 for file too large"
    
    error_data = upload_response.json()
    assert "detail" in error_data, "Error response should contain detail"
    assert "5mb" in error_data["detail"].lower() or "size" in error_data["detail"].lower(), \
        "Error should mention file size limit"

def test_upload_profile_picture_no_filename(base_url: str):
    """Test profile picture upload fails without filename"""
    import io
    
    user_data = {
        "first_name": "Profile",
        "last_name": "Picture",
        "email": f"profile.pic4{uuid4()}@example.com",
        "username": f"pp_{uuid4().hex[:8]}",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!"
    }
    
    token_data = register_and_login(base_url, user_data)
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    upload_url = f"{base_url}/users/profile-picture"
    # Upload without filename
    files = {"file": (None, io.BytesIO(b"image data"), "image/png")}
    
    upload_response = requests.post(upload_url, files=files, headers=headers)
    assert upload_response.status_code == 422, "Should return 422 for missing filename"

    
    error_data = upload_response.json()
    assert "detail" in error_data, "Error response should contain detail"

def test_upload_profile_picture_replace_existing(base_url: str):
    """Test replacing an existing profile picture"""
    import io
    from PIL import Image
    
    user_data = {
        "first_name": "Profile",
        "last_name": "Picture",
        "email": f"profile.pic5{uuid4()}@example.com",
        "username": f"pp_{uuid4().hex[:8]}",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!"
    }
    
    token_data = register_and_login(base_url, user_data)
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Upload first image
    upload_url = f"{base_url}/users/profile-picture"
    img1 = Image.new('RGB', (100, 100), color='red')
    img1_bytes = io.BytesIO()
    img1.save(img1_bytes, format='PNG')
    img1_bytes.seek(0)
    
    files1 = {"file": ("image1.png", img1_bytes, "image/png")}
    upload_response1 = requests.post(upload_url, files=files1, headers=headers)
    assert upload_response1.status_code == 200
    first_profile_pic = upload_response1.json()["profile_picture"]
    
    # Upload second image (replacement)
    img2 = Image.new('RGB', (100, 100), color='blue')
    img2_bytes = io.BytesIO()
    img2.save(img2_bytes, format='JPEG')
    img2_bytes.seek(0)
    
    files2 = {"file": ("image2.jpg", img2_bytes, "image/jpeg")}
    upload_response2 = requests.post(upload_url, files=files2, headers=headers)
    assert upload_response2.status_code == 200
    second_profile_pic = upload_response2.json()["profile_picture"]
    
    # Verify the profile picture path changed (and extension changed from PNG to JPG)
    assert second_profile_pic != first_profile_pic, "Profile picture path should have changed"
    assert second_profile_pic.endswith(".jpg"), "New file should have .jpg extension"
    
    # Verify current profile shows the new picture
    profile_url = f"{base_url}/users/me"
    profile_response = requests.get(profile_url, headers=headers)
    assert profile_response.status_code == 200
    profile_data = profile_response.json()
    assert profile_data["profile_picture"] == second_profile_pic, \
        "Profile should reflect the new profile picture"

def test_delete_profile_picture_successful(base_url: str):
    """Test successful profile picture deletion"""
    import io
    from PIL import Image
    
    user_data = {
        "first_name": "Profile",
        "last_name": "Picture",
        "email": f"profile.pic6{uuid4()}@example.com",
        "username": f"pp_{uuid4().hex[:8]}",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!"
    }
    
    token_data = register_and_login(base_url, user_data)
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # First upload a profile picture
    upload_url = f"{base_url}/users/profile-picture"
    img = Image.new('RGB', (100, 100), color='green')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    files = {"file": ("test.png", img_bytes, "image/png")}
    upload_response = requests.post(upload_url, files=files, headers=headers)
    assert upload_response.status_code == 200
    assert upload_response.json()["profile_picture"] is not None
    
    # Delete the profile picture
    delete_url = f"{base_url}/users/profile-picture"
    delete_response = requests.delete(delete_url, headers=headers)
    assert delete_response.status_code == 200, f"Profile picture deletion failed: {delete_response.text}"
    
    user_data_response = delete_response.json()
    assert user_data_response["profile_picture"] is None, "Profile picture should be None after deletion"
    
    # Verify profile picture is deleted
    profile_url = f"{base_url}/users/me"
    profile_response = requests.get(profile_url, headers=headers)
    assert profile_response.status_code == 200
    profile_data = profile_response.json()
    assert profile_data["profile_picture"] is None, "Profile picture should remain deleted"

def test_delete_profile_picture_when_none_exists(base_url: str):
    """Test deleting profile picture when user has no profile picture"""
    user_data = {
        "first_name": "Profile",
        "last_name": "Picture",
        "email": f"profile.pic7{uuid4()}@example.com",
        "username": f"pp_{uuid4().hex[:8]}",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!"
    }
    
    token_data = register_and_login(base_url, user_data)
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Try to delete when no profile picture exists
    delete_url = f"{base_url}/users/profile-picture"
    delete_response = requests.delete(delete_url, headers=headers)
    # Should still succeed (idempotent operation)
    assert delete_response.status_code == 200, "Delete should succeed even if no picture exists"
    
    user_data_response = delete_response.json()
    assert user_data_response["profile_picture"] is None, "Profile picture should be None"

def test_upload_profile_picture_unauthorized(base_url: str):
    """Test profile picture upload fails without authentication"""
    import io
    from PIL import Image
    
    upload_url = f"{base_url}/users/profile-picture"
    
    # Create test image
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    files = {"file": ("test.png", img_bytes, "image/png")}
    
    # Try without authorization
    upload_response = requests.post(upload_url, files=files)
    assert upload_response.status_code == 401, "Should return 401 without authentication"
    
    # Try with invalid token
    invalid_headers = {"Authorization": "Bearer invalid_token"}
    img_bytes.seek(0)  # Reset file pointer
    upload_response = requests.post(upload_url, files=files, headers=invalid_headers)
    assert upload_response.status_code == 401, "Should return 401 with invalid token"

def test_delete_profile_picture_unauthorized(base_url: str):
    """Test profile picture deletion fails without authentication"""
    delete_url = f"{base_url}/users/profile-picture"
    
    # Try without authorization
    delete_response = requests.delete(delete_url)
    assert delete_response.status_code == 401, "Should return 401 without authentication"
    
    # Try with invalid token
    invalid_headers = {"Authorization": "Bearer invalid_token"}
    delete_response = requests.delete(delete_url, headers=invalid_headers)
    assert delete_response.status_code == 401, "Should return 401 with invalid token"

def test_upload_profile_picture_supported_formats(base_url: str):
    """Test uploading profile pictures in all supported formats"""
    import io
    from PIL import Image
    
    user_data = {
        "first_name": "Profile",
        "last_name": "Picture",
        "email": f"profile.pic8{uuid4()}@example.com",
        "username": f"pp_{uuid4().hex[:8]}",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!"
    }
    
    token_data = register_and_login(base_url, user_data)
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    upload_url = f"{base_url}/users/profile-picture"
    
    # Test supported formats: PNG, JPEG, GIF, WebP
    formats_to_test = [
        ("PNG", "png", "image/png"),
        ("JPEG", "jpg", "image/jpeg"),
        ("GIF", "gif", "image/gif"),
        ("WEBP", "webp", "image/webp"),
    ]
    
    for format_name, ext, mime_type in formats_to_test:
        # Create image in the format
        img = Image.new('RGB', (50, 50), color=(100, 150, 200))
        img_bytes = io.BytesIO()
        
        if format_name == "WEBP":
            img.save(img_bytes, format='WEBP')
        elif format_name == "GIF":
            img.save(img_bytes, format='GIF')
        else:
            img.save(img_bytes, format=format_name)
            
        img_bytes.seek(0)
        
        files = {"file": (f"test.{ext}", img_bytes, mime_type)}
        upload_response = requests.post(upload_url, files=files, headers=headers)
        
        assert upload_response.status_code == 200, \
            f"Failed to upload {format_name} format: {upload_response.text}"
        
        user_data_response = upload_response.json()
        assert user_data_response["profile_picture"].endswith(f".{ext}"), \
            f"Uploaded {format_name} file should have .{ext} extension"
        
        # Delete before next test to avoid conflicts
        delete_url = f"{base_url}/users/profile-picture"
        requests.delete(delete_url, headers=headers)

def test_model_subtraction():
    dummy_user_id = uuid4()
    calc = Calculation.create("subtraction", dummy_user_id, [10, 3, 2])
    result = calc.get_result()
    assert result == 5, f"Subtraction result incorrect: expected 5, got {result}"

def test_model_multiplication():
    dummy_user_id = uuid4()
    calc = Calculation.create("multiplication", dummy_user_id, [2, 3, 4])
    result = calc.get_result()
    assert result == 24, f"Multiplication result incorrect: expected 24, got {result}"

def test_model_division():
    dummy_user_id = uuid4()
    calc = Calculation.create("division", dummy_user_id, [100, 2, 5])
    result = calc.get_result()
    assert result == 10, f"Division result incorrect: expected 10, got {result}"
    
    # Test division by zero error
    with pytest.raises(ValueError):
        calc_zero = Calculation.create("division", dummy_user_id, [100, 0])
        calc_zero.get_result()
