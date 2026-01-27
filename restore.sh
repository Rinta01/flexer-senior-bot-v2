#!/bin/bash

# Script to restore database from backup
# Usage: 
#   ./restore.sh backup_20260127_143547.db   (restore from .db file)
#   ./restore.sh backup_20260127_143547.sql  (restore from .sql file)

set -e

BACKUP_FILE=$1
DB_FILE="data/flexer_senior.db"

if [ -z "$BACKUP_FILE" ]; then
    echo "❌ Укажите файл бэкапа для восстановления"
    echo "Использование: ./restore.sh <backup_file>"
    echo ""
    echo "Доступные бэкапы (.db):"
    ls -lh backups/*.db 2>/dev/null | awk '{print "  - " $9 " (" $5 ", " $6 " " $7 ")"}'
    echo ""
    echo "Доступные бэкапы (.sql):"
    ls -lh backups/*.sql 2>/dev/null | awk '{print "  - " $9 " (" $5 ", " $6 " " $7 ")"}'
    exit 1
fi

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ] && [ ! -f "backups/$BACKUP_FILE" ]; then
    echo "❌ Файл бэкапа не найден: $BACKUP_FILE"
    exit 1
fi

# If only filename provided, add backups/ prefix
if [ ! -f "$BACKUP_FILE" ] && [ -f "backups/$BACKUP_FILE" ]; then
    BACKUP_FILE="backups/$BACKUP_FILE"
fi

echo "📦 Восстановление базы данных из бэкапа..."
echo "Файл бэкапа: $BACKUP_FILE"
echo "Целевой файл: $DB_FILE"
echo ""

# Create data directory if it doesn't exist
mkdir -p data

# Backup current database if it exists
if [ -f "$DB_FILE" ]; then
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_CURRENT="data/before_restore_$TIMESTAMP.db"
    echo "💾 Создаю бэкап текущей базы: $BACKUP_CURRENT"
    cp "$DB_FILE" "$BACKUP_CURRENT"
fi

# Restore from backup
echo "🔄 Восстанавливаю базу данных..."

# Check if it's a SQL dump or DB file
if [[ "$BACKUP_FILE" == *.sql ]]; then
    echo "📄 Обнаружен SQL дамп, используем sqlite3..."
    
    # Check if sqlite3 is available
    if ! command -v sqlite3 &> /dev/null; then
        echo "❌ sqlite3 не найден. Установите его или используйте .db файл"
        exit 1
    fi
    
    # Remove old database and restore from SQL
    rm -f "$DB_FILE"
    sqlite3 "$DB_FILE" < "$BACKUP_FILE"
    echo "✅ Восстановлено из SQL дампа"
else
    # Direct copy for .db files
    cp "$BACKUP_FILE" "$DB_FILE"
    echo "✅ Восстановлено из .db файла"
fi

echo ""
echo "✅ База данных успешно восстановлена!"
echo "📊 Размер восстановленной базы: $(du -h $DB_FILE | cut -f1)"
echo ""
echo "Чтобы применить изменения:"
echo "  • Если бот запущен через Docker: docker-compose restart"
echo "  • Если бот запущен локально: перезапустите бота"
