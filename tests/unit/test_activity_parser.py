"""Tests for activity input parser with whitespace handling."""

from src.handlers.activity import (
    extract_activity_location,
    is_activity_placeholder_line,
    parse_activity_multiline,
    parse_positional_activity_lines,
)


class TestParseActivityMultiline:
    """Test parse_activity_multiline function with various inputs including whitespace."""

    def test_title_only_no_whitespace(self):
        """Test parsing with only title, no extra whitespace."""
        result = parse_activity_multiline("Боулинг")
        assert result == ("Боулинг", "", "", "")

    def test_title_only_with_leading_whitespace(self):
        """Test parsing with title that has leading whitespace."""
        result = parse_activity_multiline("   Боулинг")
        assert result == ("Боулинг", "", "", "")

    def test_title_only_with_trailing_whitespace(self):
        """Test parsing with title that has trailing whitespace."""
        result = parse_activity_multiline("Боулинг   ")
        assert result == ("Боулинг", "", "", "")

    def test_title_only_with_both_whitespace(self):
        """Test parsing with title that has both leading and trailing whitespace."""
        result = parse_activity_multiline("   Боулинг   ")
        assert result == ("Боулинг", "", "", "")

    def test_title_and_description_no_whitespace(self):
        """Test parsing with title and description, no extra whitespace."""
        result = parse_activity_multiline("Боулинг\nИдём играть в боулинг на Невском")
        assert result == ("Боулинг", "Идём играть в боулинг на Невском", "", "")

    def test_title_and_description_with_whitespace_in_lines(self):
        """Test parsing with whitespace at start/end of each line."""
        result = parse_activity_multiline("   Боулинг   \n   Идём играть в боулинг на Невском   ")
        assert result == ("Боулинг", "Идём играть в боулинг на Невском", "", "")

    def test_title_and_description_with_empty_lines(self):
        """Test parsing with empty lines that should be filtered out."""
        result = parse_activity_multiline("Боулинг\n\n\nИдём играть в боулинг на Невском\n\n")
        assert result == ("Боулинг", "Идём играть в боулинг на Невском", "", "")

    def test_multiline_description_with_whitespace(self):
        """Test parsing multi-line description with various whitespace."""
        input_text = """   Боулинг   
        
        Идём играть в боулинг
        на Невском проспекте
        
        """
        result = parse_activity_multiline(input_text)
        assert result == ("Боулинг", "Идём играть в боулинг\nна Невском проспекте", "", "")

    def test_full_format_no_whitespace(self):
        """Test parsing with all fields, no extra whitespace."""
        result = parse_activity_multiline("Боулинг\nИдём играть в боулинг\n28.01 19:00")
        assert result == ("Боулинг", "Идём играть в боулинг", "28.01", "19:00")

    def test_full_format_with_whitespace_in_all_lines(self):
        """Test parsing with whitespace in all lines including date/time."""
        input_text = """   Боулинг   
           Идём играть в боулинг   
           28.01 19:00   """
        result = parse_activity_multiline(input_text)
        assert result == ("Боулинг", "Идём играть в боулинг", "28.01", "19:00")

    def test_full_format_with_tabs(self):
        """Test parsing with tabs instead of spaces."""
        input_text = "\t\tБоулинг\t\t\n\t\tИдём играть в боулинг\t\t\n\t\t28.01 19:00\t\t"
        result = parse_activity_multiline(input_text)
        assert result == ("Боулинг", "Идём играть в боулинг", "28.01", "19:00")

    def test_full_format_with_mixed_whitespace(self):
        """Test parsing with mixed tabs and spaces."""
        input_text = " \t Боулинг \t \n \t Идём играть в боулинг \t \n \t 28.01 19:00 \t "
        result = parse_activity_multiline(input_text)
        assert result == ("Боулинг", "Идём играть в боулинг", "28.01", "19:00")

    def test_date_only_with_whitespace(self):
        """Test parsing with date but no time, with whitespace."""
        result = parse_activity_multiline("   Боулинг   \n   Описание   \n   28.01   ")
        assert result == ("Боулинг", "Описание", "28.01", "")

    def test_time_only_with_whitespace(self):
        """Test parsing with time but no date, with whitespace."""
        result = parse_activity_multiline("   Боулинг   \n   Описание   \n   19:00   ")
        assert result == ("Боулинг", "Описание", "", "19:00")

    def test_date_formats_with_whitespace(self):
        """Test various date formats with whitespace."""
        # Short format
        result = parse_activity_multiline("   Боулинг   \n   28.01   ")
        assert result == ("Боулинг", "", "28.01", "")

        # Full format with year
        result = parse_activity_multiline("   Боулинг   \n   28.01.2026   ")
        assert result == ("Боулинг", "", "28.01.2026", "")

        # With dots at the end
        result = parse_activity_multiline("   Боулинг   \n   28.01.   ")
        assert result == ("Боулинг", "", "28.01.", "")

    def test_time_formats_with_whitespace(self):
        """Test various time formats with whitespace."""
        # Colon format
        result = parse_activity_multiline("   Боулинг   \n   19:00   ")
        assert result == ("Боулинг", "", "", "19:00")

        # Dash format
        result = parse_activity_multiline("   Боулинг   \n   19-30   ")
        assert result == ("Боулинг", "", "", "19-30")

    def test_empty_input(self):
        """Test parsing with empty input."""
        result = parse_activity_multiline("")
        assert result is None

    def test_only_whitespace(self):
        """Test parsing with only whitespace."""
        result = parse_activity_multiline("   \n   \n   ")
        assert result is None

    def test_real_world_telegram_paste_uses_third_line_as_location(self):
        """Test third line is treated as location in four-line user input."""
        input_text = """    Боулинг    
    
    Встречаемся в ТРЦ "Галерея"    
    Будем играть на втором этаже    
    
    28.01 19:00    
        """
        result = parse_activity_multiline(input_text)
        assert result == (
            "Боулинг",
            'Встречаемся в ТРЦ "Галерея"\nМесто: Будем играть на втором этаже',
            "28.01",
            "19:00",
        )

    def test_description_without_date_time_last_line(self):
        """Test that last line is treated as description if it doesn't contain date/time."""
        input_text = """   Боулинг   
           Идём играть в боулинг   
           Встречаемся у входа   """
        result = parse_activity_multiline(input_text)
        assert result == ("Боулинг", "Идём играть в боулинг\nВстречаемся у входа", "", "")

    def test_cyrillic_with_whitespace(self):
        """Test parsing with Cyrillic characters and whitespace."""
        input_text = """   Настольные игры   
           Играем в Манчкин и Каркассон   
           15.02 18:30   """
        result = parse_activity_multiline(input_text)
        assert result == ("Настольные игры", "Играем в Манчкин и Каркассон", "15.02", "18:30")

    def test_special_characters_with_whitespace(self):
        """Test parsing with special characters and whitespace."""
        input_text = """   Кино: "Дюна 2"   
           Смотрим в IMAX!   
           20.01 21:00   """
        result = parse_activity_multiline(input_text)
        assert result == ('Кино: "Дюна 2"', "Смотрим в IMAX!", "20.01", "21:00")

    def test_leading_trailing_newlines(self):
        """Test parsing with leading and trailing newlines."""
        input_text = "\n\n\n   Боулинг   \n   Описание   \n   28.01 19:00   \n\n\n"
        result = parse_activity_multiline(input_text)
        assert result == ("Боулинг", "Описание", "28.01", "19:00")

    def test_windows_line_endings(self):
        """Test parsing with Windows-style line endings (\\r\\n)."""
        input_text = "   Боулинг   \r\n   Описание   \r\n   28.01 19:00   "
        result = parse_activity_multiline(input_text)
        assert result == ("Боулинг", "Описание", "28.01", "19:00")

    def test_mixed_line_endings(self):
        """Test parsing with mixed line endings."""
        input_text = "   Боулинг   \r\n   Описание   \n   28.01 19:00   \r\n"
        result = parse_activity_multiline(input_text)
        assert result == ("Боулинг", "Описание", "28.01", "19:00")

    def test_labeled_format(self):
        """Test parsing activity details with explicit labels."""
        input_text = """Название: Кино
        Описание: Смотрим фильм
        Место: ТРЦ Галерея
        Дата: 28.01.2026
        Время: 19:00"""

        result = parse_activity_multiline(input_text)

        assert result == ("Кино", "Смотрим фильм\nМесто: ТРЦ Галерея", "28.01.2026", "19:00")

    def test_labeled_format_with_extended_location_label(self):
        """Test parsing activity location with a longer label."""
        input_text = """Название: Лазертаг
        Место проведения - Арена на Бауманской
        Когда: 25.05 19:00"""

        result = parse_activity_multiline(input_text)

        assert result == ("Лазертаг", "Место: Арена на Бауманской", "25.05", "19:00")

    def test_labeled_format_with_location_without_separator(self):
        """Test parsing activity location without punctuation separator."""
        input_text = """Название: Лазертаг
        Место Арена на Бауманской
        Когда 25.05 18:00"""

        result = parse_activity_multiline(input_text)

        assert result == ("Лазертаг", "Место: Арена на Бауманской", "25.05", "18:00")

    def test_labeled_when_line(self):
        """Test parsing date and time from one labeled line."""
        result = parse_activity_multiline("Название: Кино\nКогда: 28.01.2026 19:00")

        assert result == ("Кино", "", "28.01.2026", "19:00")

    def test_ignores_prompt_placeholders(self):
        """Test prompt placeholders are not saved as activity data."""
        input_text = """Название
        Кино
        Описание (необязательно)
        Смотрим фильм
        Место: адрес или место встречи (необязательно)
        28.01 19:00"""

        result = parse_activity_multiline(input_text)

        assert result == ("Кино", "Смотрим фильм", "28.01", "19:00")

    def test_positional_four_line_format_extracts_location(self):
        """Test third line is treated as location in strict four-line format."""
        input_text = """Лазертаг 4
        Стреляем пау пау 4
        Авиапарк 4
        25.05 16:00"""

        result = parse_activity_multiline(input_text)

        assert result == ("Лазертаг 4", "Стреляем пау пау 4\nМесто: Авиапарк 4", "25.05", "16:00")


class TestParsePositionalActivityLines:
    """Test strict one-line-per-field activity parser."""

    def test_four_lines(self):
        """Test title, description, location, datetime lines."""
        result = parse_positional_activity_lines(
            ["Лазертаг", "Стреляем", "Авиапарк", "25.05 16:00"]
        )

        assert result == ("Лазертаг", "Стреляем\nМесто: Авиапарк", "25.05", "16:00")

    def test_requires_four_lines(self):
        """Test parser ignores old shorter formats."""
        assert parse_positional_activity_lines(["Лазертаг", "Стреляем", "25.05 16:00"]) is None


class TestActivityPlaceholderLines:
    """Test prompt placeholder detection."""

    def test_detects_placeholder_lines(self):
        """Test placeholder strings are ignored by parser."""
        assert is_activity_placeholder_line("Название") is True
        assert is_activity_placeholder_line("Место проведения") is True
        assert is_activity_placeholder_line("Место: адрес или место встречи (необязательно)") is True
        assert is_activity_placeholder_line("28.01 19:00 (необязательно)") is True
        assert is_activity_placeholder_line("Кино") is False


class TestExtractActivityLocation:
    """Test optional location extraction from activity description."""

    def test_extracts_location_with_label(self):
        """Test extracting a labeled location line."""
        description, location = extract_activity_location(
            "Играем в настолки\nМесто: кафе Пушкин\nБерите друзей"
        )

        assert description == "Играем в настолки\nБерите друзей"
        assert location == "кафе Пушкин"

    def test_extracts_location_with_alternative_label(self):
        """Test extracting location from alternative labels."""
        description, location = extract_activity_location("Описание\nГде встречаемся - у входа")

        assert description == "Описание"
        assert location == "у входа"

    def test_extracts_location_without_separator(self):
        """Test extracting location without punctuation separator."""
        description, location = extract_activity_location("Описание\nАдрес Большая Дмитровка 1")

        assert description == "Описание"
        assert location == "Большая Дмитровка 1"

    def test_returns_description_when_location_missing(self):
        """Test description remains intact when no location label exists."""
        description, location = extract_activity_location("Встречаемся у главного входа")

        assert description == "Встречаемся у главного входа"
        assert location == ""
