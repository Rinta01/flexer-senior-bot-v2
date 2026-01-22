"""Input validation utilities."""


def validate_username(username: str | None) -> bool:
    """
    Validate Telegram username format.

    Args:
        username: Username to validate

    Returns:
        True if valid, False otherwise
    """
    if not username:
        return False

    # Username must be 5-32 characters, alphanumeric and underscores
    if len(username) < 5 or len(username) > 32:
        return False

    # Check if contains only valid characters
    return all(c.isalnum() or c == "_" for c in username)
