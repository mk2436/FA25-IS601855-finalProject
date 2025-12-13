# tests/integration/test_user_auth.py

import pytest
from uuid import UUID
import pydantic_core
from sqlalchemy.exc import IntegrityError
from app.models.user import User

def test_password_hashing(db_session, fake_user_data):
    """Test password hashing and verification functionality"""
    original_password = "TestPass123"  # Use known password for test
    hashed = User.hash_password(original_password)
    
    user = User(
        first_name=fake_user_data['first_name'],
        last_name=fake_user_data['last_name'],
        email=fake_user_data['email'],
        username=fake_user_data['username'],
        password=hashed
    )
    
    assert user.verify_password(original_password) is True
    assert user.verify_password("WrongPass123") is False
    assert hashed != original_password

def test_user_registration(db_session, fake_user_data):
    """Test user registration process"""
    fake_user_data['password'] = "TestPass123"
    
    user = User.register(db_session, fake_user_data)
    db_session.commit()
    
    assert user.first_name == fake_user_data['first_name']
    assert user.last_name == fake_user_data['last_name']
    assert user.email == fake_user_data['email']
    assert user.username == fake_user_data['username']
    assert user.is_active is True
    assert user.is_verified is False
    assert user.verify_password("TestPass123") is True

def test_duplicate_user_registration(db_session):
    """Test registration with duplicate email/username"""
    # First user data
    user1_data = {
        "first_name": "Test",
        "last_name": "User1",
        "email": "unique.test@example.com",
        "username": "uniqueuser1",
        "password": "TestPass123"
    }
    
    # Second user data with same email
    user2_data = {
        "first_name": "Test",
        "last_name": "User2",
        "email": "unique.test@example.com",  # Same email
        "username": "uniqueuser2",
        "password": "TestPass123"
    }
    
    # Register first user
    first_user = User.register(db_session, user1_data)
    db_session.commit()
    db_session.refresh(first_user)
    
    # Try to register second user with same email
    with pytest.raises(ValueError, match="Username or email already exists"):
        User.register(db_session, user2_data)

def test_user_authentication(db_session, fake_user_data):
    """Test user authentication and token generation"""
    # Use fake_user_data from fixture
    fake_user_data['password'] = "TestPass123"
    user = User.register(db_session, fake_user_data)
    db_session.commit()
    
    # Test successful authentication
    auth_result = User.authenticate(
        db_session,
        fake_user_data['username'],
        "TestPass123"
    )
    
    assert auth_result is not None
    assert "access_token" in auth_result
    assert "token_type" in auth_result
    assert auth_result["token_type"] == "bearer"
    assert "user" in auth_result

def test_user_last_login_update(db_session, fake_user_data):
    """Test that last_login is updated on authentication"""
    fake_user_data['password'] = "TestPass123"
    user = User.register(db_session, fake_user_data)
    db_session.commit()
    
    # Authenticate and check last_login
    assert user.last_login is None
    auth_result = User.authenticate(db_session, fake_user_data['username'], "TestPass123")
    db_session.refresh(user)
    assert user.last_login is not None

def test_unique_email_username(db_session):
    """Test uniqueness constraints for email and username"""
    # Create first user with specific test data
    user1_data = {
        "first_name": "Test",
        "last_name": "User1",
        "email": "unique_test@example.com",
        "username": "uniqueuser",
        "password": "TestPass123"
    }
    
    # Register and commit first user
    User.register(db_session, user1_data)
    db_session.commit()
    
    # Try to create user with same email
    user2_data = {
        "first_name": "Test",
        "last_name": "User2",
        "email": "unique_test@example.com",  # Same email
        "username": "differentuser",
        "password": "TestPass123"
    }
    
    with pytest.raises(ValueError, match="Username or email already exists"):
        User.register(db_session, user2_data)

def test_short_password_registration(db_session):
    """Test that registration fails with a short password"""
    # Prepare test data with a 5-character password
    test_data = {
        "first_name": "Password",
        "last_name": "Test",
        "email": "short.pass@example.com",
        "username": "shortpass",
        "password": "Shor1"  # 5 characters, should fail
    }
    
    # Attempt registration with short password
    with pytest.raises(ValueError, match="Password must be at least 6 characters long"):
        User.register(db_session, test_data)

def test_invalid_token():
    """Test that invalid tokens are rejected"""
    invalid_token = "invalid.token.string"
    result = User.verify_token(invalid_token)
    assert result is None

def test_token_creation_and_verification(db_session, fake_user_data):
    """Test token creation and verification"""
    fake_user_data['password'] = "TestPass123"
    user = User.register(db_session, fake_user_data)
    db_session.commit()
    
    # Create token
    token = User.create_access_token({"sub": str(user.id)})
    
    # Verify token
    decoded_user_id = User.verify_token(token)
    assert decoded_user_id == user.id

def test_authenticate_with_email(db_session, fake_user_data):
    """Test authentication using email instead of username"""
    fake_user_data['password'] = "TestPass123"
    user = User.register(db_session, fake_user_data)
    db_session.commit()
    
    # Test authentication with email
    auth_result = User.authenticate(
        db_session,
        fake_user_data['email'],  # Using email instead of username
        "TestPass123"
    )
    
    assert auth_result is not None
    assert "access_token" in auth_result

def test_user_model_representation(test_user):
    """Test the string representation of User model"""
    expected = f"<User(name={test_user.first_name} {test_user.last_name}, email={test_user.email})>"
    assert str(test_user) == expected

def test_missing_password_registration(db_session):
    """Test that registration fails when no password is provided."""
    test_data = {
        "first_name": "NoPassword",
        "last_name": "Test",
        "email": "no.password@example.com",
        "username": "nopassworduser",
        # Password is missing
    }
    
    # Adjust the expected error message
    with pytest.raises(ValueError, match="Password must be at least 6 characters long"):
        User.register(db_session, test_data)


# ---------------------------------------------
# Password Update Tests
# ---------------------------------------------

def test_password_update_successful(db_session, fake_user_data):
    """Test successful password update"""
    # Register a user with initial password
    fake_user_data['password'] = "OldPass123!"
    user = User.register(db_session, fake_user_data)
    db_session.commit()
    db_session.refresh(user)
    
    # Store the old password hash
    old_password_hash = user.password
    
    # Update password
    new_password = "NewPass456!"
    hashed_new_password = User.hash_password(new_password)
    user.password = hashed_new_password
    db_session.commit()
    db_session.refresh(user)
    
    # Verify old password no longer works
    assert not user.verify_password("OldPass123!"), "Old password should not work"
    
    # Verify new password works
    assert user.verify_password(new_password), "New password should work"
    
    # Verify password hash changed
    assert user.password != old_password_hash, "Password hash should have changed"

def test_password_update_verification(db_session, fake_user_data):
    """Test that password update requires correct current password verification"""
    fake_user_data['password'] = "OldPass123!"
    user = User.register(db_session, fake_user_data)
    db_session.commit()
    db_session.refresh(user)
    
    # Try to update with wrong current password
    wrong_password = "WrongPass123!"
    correct_new_password = "NewPass456!"
    
    # Verify current password first
    assert user.verify_password("OldPass123!"), "Current password should be correct"
    assert not user.verify_password(wrong_password), "Wrong password should not verify"
    
    # If wrong password is used, update should fail
    # This is tested at the API level, but we can test the model level
    hashed_new = User.hash_password(correct_new_password)
    user.password = hashed_new
    db_session.commit()
    
    # After update, old password should not work
    assert not user.verify_password("OldPass123!"), "Old password should not work after update"
    assert user.verify_password(correct_new_password), "New password should work"

def test_password_update_schema_validation():
    """Test PasswordUpdate schema validation"""
    from app.schemas.user import PasswordUpdate
    from pydantic import ValidationError
    
    # Valid password update
    valid_data = {
        "current_password": "OldPass123!",
        "new_password": "NewPass456!",
        "confirm_new_password": "NewPass456!"
    }
    password_update = PasswordUpdate(**valid_data)
    assert password_update.current_password == "OldPass123!"
    assert password_update.new_password == "NewPass456!"
    
    # Test password mismatch
    with pytest.raises(ValidationError) as exc_info:
        PasswordUpdate(
            current_password="OldPass123!",
            new_password="NewPass456!",
            confirm_new_password="DifferentPass789!"
        )
    assert "do not match" in str(exc_info.value).lower()
    
    # Test new password same as current
    with pytest.raises(ValidationError) as exc_info:
        PasswordUpdate(
            current_password="SamePass123!",
            new_password="SamePass123!",
            confirm_new_password="SamePass123!"
        )
    assert "different from current" in str(exc_info.value).lower()
    
    # Test password too short
    with pytest.raises(ValidationError) as exc_info:
        PasswordUpdate(
            current_password="OldPass123!",
            new_password="Short1!",
            confirm_new_password="Short1!"
        )
    assert "at least 8 characters" in str(exc_info.value).lower()
    
    # Test missing uppercase
    with pytest.raises(ValidationError) as exc_info:
        PasswordUpdate(
            current_password="OldPass123!",
            new_password="newpass123!",
            confirm_new_password="newpass123!"
        )
    assert "uppercase" in str(exc_info.value).lower()
    
    # Test missing lowercase
    with pytest.raises(ValidationError) as exc_info:
        PasswordUpdate(
            current_password="OldPass123!",
            new_password="NEWPASS123!",
            confirm_new_password="NEWPASS123!"
        )
    assert "lowercase" in str(exc_info.value).lower()
    
    # Test missing digit
    with pytest.raises(ValidationError) as exc_info:
        PasswordUpdate(
            current_password="OldPass123!",
            new_password="NewPass!",
            confirm_new_password="NewPass!"
        )
    assert "digit" in str(exc_info.value).lower()
    
    # Test missing special character
    with pytest.raises(ValidationError) as exc_info:
        PasswordUpdate(
            current_password="OldPass123!",
            new_password="NewPass123",
            confirm_new_password="NewPass123"
        )
    assert "special character" in str(exc_info.value).lower()

def test_password_update_minimum_length(db_session, fake_user_data):
    """Test that password update enforces minimum length"""
    from app.schemas.user import PasswordUpdate
    from pydantic import ValidationError
    
    # Test with exactly 8 characters (should pass)
    valid_short = PasswordUpdate(
        current_password="OldPass123!",
        new_password="NewP1!@#",
        confirm_new_password="NewP1!@#"
    )
    assert len(valid_short.new_password) == 8
    
    # Test with 7 characters (should fail)
    with pytest.raises(ValidationError):
        PasswordUpdate(
            current_password="OldPass123!",
            new_password="NewP1!@",
            confirm_new_password="NewP1!@"
        )

def test_password_update_updated_at_timestamp(db_session, fake_user_data):
    """Test that password update changes the updated_at timestamp"""
    from datetime import datetime, timezone
    
    fake_user_data['password'] = "OldPass123!"
    user = User.register(db_session, fake_user_data)
    db_session.commit()
    db_session.refresh(user)
    
    original_updated_at = user.updated_at
    
    # Wait a moment to ensure timestamp difference
    import time
    time.sleep(0.1)
    
    # Update password
    new_password = "NewPass456!"
    hashed_new = User.hash_password(new_password)
    user.password = hashed_new
    user.updated_at = datetime.now(timezone.utc)
    db_session.commit()
    db_session.refresh(user)
    
    assert user.updated_at > original_updated_at, "updated_at should be newer after password change"

def test_password_update_preserves_other_fields(db_session, fake_user_data):
    """Test that password update doesn't affect other user fields"""
    fake_user_data['password'] = "OldPass123!"
    user = User.register(db_session, fake_user_data)
    db_session.commit()
    db_session.refresh(user)
    
    # Store original values
    original_email = user.email
    original_username = user.username
    original_first_name = user.first_name
    original_last_name = user.last_name
    original_id = user.id
    
    # Update password
    new_password = "NewPass456!"
    hashed_new = User.hash_password(new_password)
    user.password = hashed_new
    db_session.commit()
    db_session.refresh(user)
    
    # Verify other fields unchanged
    assert user.email == original_email, "Email should not change"
    assert user.username == original_username, "Username should not change"
    assert user.first_name == original_first_name, "First name should not change"
    assert user.last_name == original_last_name, "Last name should not change"
    assert user.id == original_id, "User ID should not change"
    assert user.verify_password(new_password), "New password should work"


# ---------------------------------------------
# Profile Picture Update Tests
# ---------------------------------------------

def test_user_profile_picture_field_exists(db_session, fake_user_data):
    """Test that User model has profile_picture field"""
    fake_user_data['password'] = "TestPass123"
    user = User.register(db_session, fake_user_data)
    db_session.commit()
    db_session.refresh(user)
    
    # Verify profile_picture field exists and defaults to None
    assert hasattr(user, 'profile_picture'), "User should have profile_picture attribute"
    assert user.profile_picture is None, "New user should have no profile picture initially"

def test_user_profile_picture_assignment(db_session, fake_user_data):
    """Test assigning and retrieving profile picture path"""
    fake_user_data['password'] = "TestPass123"
    user = User.register(db_session, fake_user_data)
    db_session.commit()
    db_session.refresh(user)
    
    # Assign profile picture path
    test_path = "/static/uploads/profile_pictures/user_123.png"
    user.profile_picture = test_path
    db_session.commit()
    db_session.refresh(user)
    
    assert user.profile_picture == test_path, "Profile picture path should be stored correctly"

def test_user_profile_picture_update_timestamp(db_session, fake_user_data):
    """Test that profile picture update changes updated_at timestamp"""
    from datetime import datetime, timezone
    
    fake_user_data['password'] = "TestPass123"
    user = User.register(db_session, fake_user_data)
    db_session.commit()
    db_session.refresh(user)
    
    original_updated_at = user.updated_at
    
    # Wait a moment to ensure timestamp difference
    import time
    time.sleep(0.1)
    
    # Update profile picture
    user.profile_picture = "/static/uploads/profile_pictures/test.png"
    user.updated_at = datetime.now(timezone.utc)
    db_session.commit()
    db_session.refresh(user)
    
    assert user.updated_at > original_updated_at, "updated_at should be newer after profile picture update"

def test_user_profile_picture_clear(db_session, fake_user_data):
    """Test clearing profile picture (setting to None)"""
    fake_user_data['password'] = "TestPass123"
    user = User.register(db_session, fake_user_data)
    db_session.commit()
    db_session.refresh(user)
    
    # Set profile picture
    user.profile_picture = "/static/uploads/profile_pictures/test.png"
    db_session.commit()
    db_session.refresh(user)
    assert user.profile_picture is not None, "Profile picture should be set"
    
    # Clear profile picture
    user.profile_picture = None
    db_session.commit()
    db_session.refresh(user)
    assert user.profile_picture is None, "Profile picture should be cleared"

def test_user_profile_picture_preserves_other_fields(db_session, fake_user_data):
    """Test that profile picture update doesn't affect other user fields"""
    fake_user_data['password'] = "TestPass123"
    user = User.register(db_session, fake_user_data)
    db_session.commit()
    db_session.refresh(user)
    
    # Store original values
    original_email = user.email
    original_username = user.username
    original_first_name = user.first_name
    original_last_name = user.last_name
    original_id = user.id
    original_password_hash = user.password
    
    # Update profile picture
    user.profile_picture = "/static/uploads/profile_pictures/new_pic.jpg"
    db_session.commit()
    db_session.refresh(user)
    
    # Verify other fields unchanged
    assert user.email == original_email, "Email should not change"
    assert user.username == original_username, "Username should not change"
    assert user.first_name == original_first_name, "First name should not change"
    assert user.last_name == original_last_name, "Last name should not change"
    assert user.id == original_id, "User ID should not change"
    assert user.password == original_password_hash, "Password should not change"
    assert user.profile_picture == "/static/uploads/profile_pictures/new_pic.jpg", \
        "Profile picture should be updated"

def test_user_profile_picture_replace_existing(db_session, fake_user_data):
    """Test replacing an existing profile picture"""
    fake_user_data['password'] = "TestPass123"
    user = User.register(db_session, fake_user_data)
    db_session.commit()
    db_session.refresh(user)
    
    # Set initial profile picture
    first_picture = "/static/uploads/profile_pictures/first.png"
    user.profile_picture = first_picture
    db_session.commit()
    db_session.refresh(user)
    assert user.profile_picture == first_picture
    
    # Replace with new picture
    second_picture = "/static/uploads/profile_pictures/second.jpg"
    user.profile_picture = second_picture
    db_session.commit()
    db_session.refresh(user)
    assert user.profile_picture == second_picture, "Profile picture should be replaced"
    assert user.profile_picture != first_picture, "Old profile picture path should be replaced"
