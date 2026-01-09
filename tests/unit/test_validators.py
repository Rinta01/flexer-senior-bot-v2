"""Unit tests for validators."""

from src.utils.validators import format_user_mention, validate_username


def test_validate_username_valid():
    """Test valid username validation."""
    assert validate_username("testuser") is True
    assert validate_username("test_user_123") is True
    assert validate_username("a1234") is True  # Exactly 5 chars


def test_validate_username_too_short():
    """Test username too short."""
    assert validate_username("ab") is False
    assert validate_username("test") is False


def test_validate_username_too_long():
    """Test username too long."""
    assert validate_username("a" * 33) is False


def test_validate_username_invalid_characters():
    """Test username with invalid characters."""
    assert validate_username("test-user") is False
    assert validate_username("test user") is False
    assert validate_username("test.user") is False


def test_validate_username_empty():
    """Test empty username."""
    assert validate_username("") is False
    assert validate_username(None) is False


def test_format_user_mention_with_username():
    """Test formatting mention with username."""
    mention = format_user_mention(123456, "testuser")
    assert mention == "@testuser"


def test_format_user_mention_without_username():
    """Test formatting mention without username."""
    mention = format_user_mention(123456, None)
    assert "tg://user?id=123456" in mention


def test_format_user_mention_invalid_username():
    """Test formatting mention with invalid username."""
    mention = format_user_mention(123456, "invalid user")
    assert "tg://user?id=123456" in mention
