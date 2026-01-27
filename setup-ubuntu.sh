#!/bin/bash

# Setup script for Ubuntu/Linux systems
# Prepares directories with correct permissions for Docker

set -e

echo "🚀 Настройка окружения для Flexer Senior Bot"
echo ""

# Get current user's UID and GID
CURRENT_UID=$(id -u)
CURRENT_GID=$(id -g)

echo "📋 Информация о пользователе:"
echo "  UID: $CURRENT_UID"
echo "  GID: $CURRENT_GID"
echo "  User: $(whoami)"
echo ""

# Create directories if they don't exist
echo "📁 Создание директорий..."
mkdir -p data backups

# Set permissions
echo "🔐 Установка прав доступа..."
chmod 755 data backups

echo "✅ Директории созданы с правильными правами"
echo ""

# Add UID/GID to .env if not exists
if ! grep -q "UID=" .env 2>/dev/null; then
    echo "📝 Добавление UID/GID в .env..."
    echo "" >> .env
    echo "# Docker user permissions" >> .env
    echo "UID=$CURRENT_UID" >> .env
    echo "GID=$CURRENT_GID" >> .env
    echo "✅ UID/GID добавлены в .env"
else
    echo "ℹ️  UID/GID уже в .env"
fi

echo ""
echo "✅ Настройка завершена!"
echo ""
echo "Теперь можно запускать бота:"
echo "  docker-compose up -d"
echo ""
echo "Проверить логи:"
echo "  docker-compose logs -f"
