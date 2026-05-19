#!/bin/bash
# Скрипт управления ботом Флексер старший

cd "$(dirname "$0")"

get_db_path() {
    if [ -n "$DB_PATH" ]; then
        echo "$DB_PATH"
    elif [ -f "data/flexer_senior.db" ]; then
        echo "data/flexer_senior.db"
    else
        echo "flexer_senior.db"
    fi
}

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
        DB_FILE="$(get_db_path)"
        if [ -f "$DB_FILE" ]; then
            echo "✅ База данных существует"
            ls -lh "$DB_FILE"
            echo ""
            echo "Таблицы в базе данных:"
            sqlite3 "$DB_FILE" ".tables"
            echo ""
            echo "Количество записей:"
            for table in $(sqlite3 "$DB_FILE" "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"); do
                count=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM $table;")
                echo "  $table: $count"
            done
            if sqlite3 "$DB_FILE" "SELECT auto_pick_enabled FROM duty_pools LIMIT 1;" >/dev/null 2>&1; then
                echo ""
                echo "Пулы и авто-выбор:"
                sqlite3 -header -column "$DB_FILE" \
                    "SELECT id, group_id, group_title, auto_pick_enabled FROM duty_pools ORDER BY id;"
            else
                echo ""
                echo "ℹ️ В duty_pools пока нет auto_pick_enabled."
                echo "Колонка будет добавлена автоматически при следующем старте бота."
            fi
        else
            echo "❌ База данных не найдена: $DB_FILE"
            echo "Можно указать путь явно: DB_PATH=/path/to/flexer_senior.db ./run.sh check-db"
        fi
        ;;
    logs)
        echo "📋 Логи бота (последние 50 строк)..."
        if docker compose logs --tail=50 bot 2>/dev/null; then
            exit 0
        fi

        shopt -s nullglob
        log_files=(logs/*.log)
        if [ ${#log_files[@]} -gt 0 ]; then
            tail -50 "${log_files[@]}"
        else
            echo "Логи не найдены."
            echo "Если бот запущен через Docker, убедитесь, что Docker daemon запущен."
            echo "Если бот запущен через ./run.sh start, логи выводятся прямо в текущий терминал."
        fi
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
