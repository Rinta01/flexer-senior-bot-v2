"""Unit tests for activity.py pure functions."""

from datetime import datetime

from src.database.models import DutyAssignment, DutyStatus, TelegramUser
from src.handlers.activity import (
    format_activity_info,
    parse_activity_input,
    parse_datetime,
    validate_duty_permissions,
)


class TestParseDateTime:
    """Tests for parse_datetime function."""

    def test_parse_full_date_with_colon_time(self):
        """Test parsing full date with colon-separated time."""
        result = parse_datetime("15.01.2026", "19:30")
        assert result is not None
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 19
        assert result.minute == 30

    def test_parse_short_date_with_colon_time(self):
        """Test parsing short date (no year) with colon time."""
        result = parse_datetime("15.01", "19:30")
        assert result is not None
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 19
        assert result.minute == 30

    def test_parse_full_date_with_dash_time(self):
        """Test parsing full date with dash-separated time."""
        result = parse_datetime("15.01.2026", "19-30")
        assert result is not None
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 19
        assert result.minute == 30

    def test_parse_short_date_with_dash_time(self):
        """Test parsing short date with dash time."""
        result = parse_datetime("15.01", "19-30")
        assert result is not None
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 19
        assert result.minute == 30

    def test_parse_invalid_date_format(self):
        """Test parsing invalid date format returns None."""
        result = parse_datetime("2026-01-15", "19:30")
        assert result is None

    def test_parse_invalid_time_format(self):
        """Test parsing invalid time format returns None."""
        result = parse_datetime("15.01.2026", "7pm")
        assert result is None

    def test_parse_empty_strings(self):
        """Test parsing empty strings returns None."""
        result = parse_datetime("", "")
        assert result is None


class TestParseActivityInput:
    """Tests for parse_activity_input function."""

    def test_parse_valid_input(self):
        """Test parsing valid activity input."""
        result = parse_activity_input("Party | Fun event | 15.01.2026 | 19:30")
        assert result is not None
        assert result == ("Party", "Fun event", "15.01.2026", "19:30")

    def test_parse_with_extra_spaces(self):
        """Test parsing input with extra spaces around separators."""
        result = parse_activity_input("Party  |  Fun event  |  15.01.2026  |  19:30")
        assert result is not None
        assert result == ("Party", "Fun event", "15.01.2026", "19:30")

    def test_parse_with_pipe_in_description(self):
        """Test parsing when description contains pipe character."""
        # This will split into more than 4 parts - should return None
        result = parse_activity_input("Party | Fun | Great | 15.01.2026 | 19:30")
        assert result is None

    def test_parse_missing_parts(self):
        """Test parsing with missing parts returns None."""
        result = parse_activity_input("Party | Fun event | 15.01.2026")
        assert result is None

    def test_parse_empty_part(self):
        """Test parsing with empty part returns None."""
        result = parse_activity_input("Party |  | 15.01.2026 | 19:30")
        assert result is None

    def test_parse_all_empty_parts(self):
        """Test parsing with all empty parts returns None."""
        result = parse_activity_input(" | | | ")
        assert result is None

    def test_parse_empty_string(self):
        """Test parsing empty string returns None."""
        result = parse_activity_input("")
        assert result is None


class TestValidateDutyPermissions:
    """Tests for validate_duty_permissions function."""

    def test_valid_permissions_confirmed_duty(self):
        """Test validation passes for confirmed duty assigned to user."""
        duty = DutyAssignment(
            id=1,
            pool_id=123,
            user_id=456,
            week_number=5,
            status=DutyStatus.CONFIRMED,
        )
        assert validate_duty_permissions(duty, 456) is True

    def test_invalid_permissions_wrong_user(self):
        """Test validation fails for different user."""
        duty = DutyAssignment(
            id=1,
            pool_id=123,
            user_id=456,
            week_number=5,
            status=DutyStatus.CONFIRMED,
        )
        assert validate_duty_permissions(duty, 789) is False

    def test_invalid_permissions_pending_status(self):
        """Test validation fails for pending duty."""
        duty = DutyAssignment(
            id=1,
            pool_id=123,
            user_id=456,
            week_number=5,
            status=DutyStatus.PENDING,
        )
        assert validate_duty_permissions(duty, 456) is False

    def test_invalid_permissions_declined_status(self):
        """Test validation fails for declined duty."""
        duty = DutyAssignment(
            id=1,
            pool_id=123,
            user_id=456,
            week_number=5,
            status=DutyStatus.DECLINED,
        )
        assert validate_duty_permissions(duty, 456) is False


class TestFormatActivityInfo:
    """Tests for format_activity_info function."""

    def test_format_confirmed_duty_with_activity(self):
        """Test formatting confirmed duty with activity set."""
        duty = DutyAssignment(
            id=1,
            pool_id=123,
            user_id=456,
            week_number=5,
            status=DutyStatus.CONFIRMED,
            activity_title="Weekly Party",
            activity_description="Fun event for everyone",
            activity_datetime=datetime(2026, 2, 5, 19, 30),
        )
        user = TelegramUser(id=456, user_id=456, username="john_doe", first_name="John")

        result = format_activity_info(duty, user)

        assert "🎯 <b>Дежурный недели</b>" in result
        assert "@john_doe" in result
        assert "✅ Подтверждено" in result
        assert "📅 <b>Активность недели:</b>" in result
        assert "Weekly Party" in result
        assert "Fun event for everyone" in result
        assert "05.02.2026 в 19:30" in result
        assert "До встречи, не теряемся 💪" in result

    def test_format_confirmed_duty_without_activity(self):
        """Test formatting confirmed duty without activity set."""
        duty = DutyAssignment(
            id=1,
            pool_id=123,
            user_id=456,
            week_number=5,
            status=DutyStatus.CONFIRMED,
            activity_title=None,
        )
        user = TelegramUser(id=456, user_id=456, username="john_doe", first_name="John")

        result = format_activity_info(duty, user)

        assert "🎯 <b>Дежурный недели</b>" in result
        assert "@john_doe" in result
        assert "✅ Подтверждено" in result
        assert "❓ Активность пока не установлена." in result
        assert "💡" in result
        assert "/set_activity" in result
        assert "Увидимся на мероприятии" not in result

    def test_format_pending_duty(self):
        """Test formatting pending duty."""
        duty = DutyAssignment(
            id=1,
            pool_id=123,
            user_id=456,
            week_number=5,
            status=DutyStatus.PENDING,
        )
        user = TelegramUser(id=456, user_id=456, username="john_doe", first_name="John")

        result = format_activity_info(duty, user)

        assert "🎯 <b>Дежурный недели</b>" in result
        assert "@john_doe" in result
        assert "⏳ Ожидает подтверждения" in result
        assert "❓ Активность пока не установлена." in result
        assert "⏳ Ожидаем подтверждения от дежурного." in result
        assert "💡" not in result

    def test_format_duty_with_activity_no_description(self):
        """Test formatting duty with activity but no description."""
        duty = DutyAssignment(
            id=1,
            pool_id=123,
            user_id=456,
            week_number=5,
            status=DutyStatus.CONFIRMED,
            activity_title="Quick Meeting",
            activity_description=None,
            activity_datetime=datetime(2026, 2, 5, 19, 30),
        )
        user = TelegramUser(id=456, user_id=456, username="john_doe", first_name="John")

        result = format_activity_info(duty, user)

        assert "Quick Meeting" in result
        assert "<b>Описание:</b>" not in result
        assert "05.02.2026 в 19:30" in result

    def test_format_duty_with_activity_no_datetime(self):
        """Test formatting duty with activity but no datetime."""
        duty = DutyAssignment(
            id=1,
            pool_id=123,
            user_id=456,
            week_number=5,
            status=DutyStatus.CONFIRMED,
            activity_title="TBD Event",
            activity_description="Details coming soon",
            activity_datetime=None,
        )
        user = TelegramUser(id=456, user_id=456, username="john_doe", first_name="John")

        result = format_activity_info(duty, user)

        assert "TBD Event" in result
        assert "Details coming soon" in result
        assert "<b>Когда:</b>" not in result

    def test_format_duty_with_user_without_username(self):
        """Test formatting duty when user has no username."""
        duty = DutyAssignment(
            id=1,
            pool_id=123,
            user_id=456,
            week_number=5,
            status=DutyStatus.CONFIRMED,
        )
        user = TelegramUser(id=456, user_id=456, username=None, first_name="John")

        result = format_activity_info(duty, user)

        assert "🎯 <b>Дежурный недели</b>" in result
        # Should contain user mention without @ symbol
        assert "tg://user?id=456" in result
        assert "John" in result

    def test_format_duty_with_skipped_status(self):
        """Test formatting duty when duty was declined (SKIPPED status)."""
        duty = DutyAssignment(
            id=1,
            pool_id=123,
            user_id=456,
            week_number=5,
            status=DutyStatus.SKIPPED,
        )
        user = TelegramUser(id=456, user_id=456, username="john_doe", first_name="John")

        result = format_activity_info(duty, user)

        assert "🎯 <b>Дежурный недели</b>" in result
        assert "@john_doe" in result
        assert "⏭️ Пропущено" in result
        assert "❓ Активность пока не установлена." in result
        assert "❌ Дежурный отказался от дежурства на эту неделю." in result
        assert "⏳ Ожидаем подтверждения" not in result
        assert "💡" not in result
