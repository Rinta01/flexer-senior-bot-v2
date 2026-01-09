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


def format_user_mention(user_id: int, username: str | None = None) -> str:
    """
    Format user mention for Telegram message.

    Args:
        user_id: Telegram user ID
        username: Telegram username (if available)

    Returns:
        Formatted mention string
    """
    if username and validate_username(username):
        return f"@{username}"
    return f"[User {user_id}](tg://user?id={user_id})"
