#!/bin/bash
# Скрипт управления ботом Флексер старший

cd "$(dirname "$0")"

case "$1" in
    start)
        echo "🚀 Запуск бота..."
        ./venv/bin/python -m src.bot
        ;;
    test)
        echo "🧪 Запуск тестов..."
        ./venv/bin/pytest tests/ -v
        ;;
    test-quick)
        echo "⚡ Быстрый запуск тестов..."
        ./venv/bin/pytest tests/ -v --tb=no -q
        ;;
    check-db)
        echo "📊 Проверка базы данных..."
        if [ -f "flexer_senior.db" ]; then
            echo "✅ База данных существует"
            ls -lh flexer_senior.db
            echo ""
            echo "Таблицы в базе данных:"
            sqlite3 flexer_senior.db ".tables"
        else
            echo "❌ База данных не найдена"
        fi
        ;;
    logs)
        echo "📋 Логи бота (последние 50 строк)..."
        tail -50 logs/*.log 2>/dev/null || echo "Логи не найдены"
        ;;
    clean)
        echo "🧹 Очистка..."
        rm -f flexer_senior.db
        rm -rf __pycache__ src/__pycache__ tests/__pycache__
        rm -rf .pytest_cache htmlcov .coverage
        echo "✅ Очистка завершена"
        ;;
    *)
        echo "Флексер старший - Управление ботом"
        echo ""
        echo "Использование: ./run.sh [команда]"
        echo ""
        echo "Команды:"
        echo "  start       - Запустить бота"
        echo "  test        - Запустить все тесты"
        echo "  test-quick  - Быстрый запуск тестов"
        echo "  check-db    - Проверить базу данных"
        echo "  logs        - Показать логи"
        echo "  clean       - Очистить БД и временные файлы"
        echo ""
        echo "Примеры:"
        echo "  ./run.sh start      # Запустить бота"
        echo "  ./run.sh test       # Запустить тесты"
        echo "  ./run.sh check-db   # Проверить БД"
        ;;
esac
