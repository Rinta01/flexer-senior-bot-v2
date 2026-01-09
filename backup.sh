#!/bin/bash
DB_FILE="flexer_senior.db"
BACKUP_DIR="backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

mkdir -p $BACKUP_DIR

# SQLite dump
sqlite3 $DB_FILE ".dump" > "$BACKUP_DIR/backup_$TIMESTAMP.sql"

# Простое копирование файла
cp $DB_FILE "$BACKUP_DIR/backup_$TIMESTAMP.db"

# Удаление старых бекапов (старше 30 дней)
find $BACKUP_DIR -name "backup_*.db" -mtime +30 -delete
find $BACKUP_DIR -name "backup_*.sql" -mtime +30 -delete

echo "✅ Backup created: backup_$TIMESTAMP"