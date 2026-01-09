# 🛠️ Development Guide - Флексер старший

## Для разработчиков

---

## IDE Setup

### VS Code

Установить расширения:

- Python
- Pylance
- pytest
- Docker

### PyCharm

Встроенная поддержка Python, просто откройте проект.

---

## Локальная разработка

### 1. Подготовка

```bash
# Клонировать и войти
git clone https://github.com/Rinta01/flexer-senior-bot-v2.git
cd flexer-senior-bot-v2

# Создать venv
python3.12 -m venv venv
source venv/bin/activate

# Установить с dev зависимостями
pip install -e ".[dev,db]"
```

### 2. Настроить .env

```bash
cp .env.example .env

# Отредактировать:
# BOT_TOKEN=<ваш_токен>
# DATABASE_URL=sqlite+aiosqlite:///./flexer_senior.db  # SQLite используется по умолчанию
```

**Примечание:** Проект использует SQLite для простоты локальной разработки. База данных будет автоматически создана при первом запуске.

```bash
python -m src.bot

# Или с горячей перезагрузкой (требует watchdog)
pip install watchdog[watchmedo]
watchmedo auto-restart -d src -p '*.py' -- python -m src.bot
```

---

## Рабочий процесс

### 1. Создать feature branch

```bash
git checkout -b feature/feature-name
# или
git checkout -b fix/bug-name
```

### 2. Написать код

```python
# Пример: добавить новый обработчик

# src/handlers/my_handler.py
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

@router.message(Command("mycommand"))
async def my_command(message: Message) -> None:
    """Handle /mycommand."""
    await message.answer("Response")
```

### 3. Написать тесты

```python
# tests/unit/test_my_handler.py
import pytest

@pytest.mark.asyncio
async def test_my_command(db_session):
    """Test my command."""
    # arrange

    # act

    # assert
```

### 4. Проверить качество

```bash
# Линтинг
ruff check src/

# Форматирование
black src/

# Типы
mypy src/

# Тесты
pytest -v

# Все вместе
./check-code.sh  # (создайте этот файл)
```

### 5. Коммит

```bash
git add .
git commit -m "feat: add my feature"
# или
git commit -m "fix: fix bug in handler"
```

### 6. Push и PR

```bash
git push origin feature/feature-name
# Создайте Pull Request на GitHub
```

---

## Структура file

### Добавить новый обработчик команды

#### 1. Создать файл `src/handlers/my_cmd.py`

```python
"""Handler for /mycommand."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.database.engine import db_manager
from src.services.user_manager import UserManager
from src.utils.logger import setup_logging

logger = setup_logging(__name__)

router = Router()


@router.message(Command("mycommand"))
async def my_command(message: Message) -> None:
    """Handle /mycommand command."""
    try:
        # Get session and do something
        async with db_manager.async_session() as session:
            user_manager = UserManager(session)
            # ... logic ...

        await message.answer("Result")
        logger.info(f"Handled /mycommand from {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error in my_command: {e}")
        await message.answer("❌ An error occurred.")
```

#### 2. Зарегистрировать в `src/bot.py`

```python
def setup_handlers(self) -> None:
    """Register command handlers."""
    logger.info("Setting up handlers...")

    # Добавить эту строку:
    from src.handlers import my_cmd
    self.dp.include_router(my_cmd.router)
```

#### 3. Написать тесты в `tests/unit/test_my_cmd.py`

```python
"""Tests for my_cmd handler."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# Test functions
```

#### 4. Запустить тесты

```bash
pytest tests/unit/test_my_cmd.py -v
```

---

### Добавить новый сервис

#### 1. Создать `src/services/my_service.py`

```python
"""My new service."""

from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.logger import setup_logging

logger = setup_logging(__name__)


class MyService:
    """Service for some functionality."""

    def __init__(self, session: AsyncSession):
        """Initialize service."""
        self.session = session

    async def do_something(self) -> str:
        """Do something and return result."""
        try:
            # Logic here
            return "result"
        except Exception as e:
            logger.error(f"Error: {e}")
            return None
```

#### 2. Использовать в обработчике

```python
from src.services.my_service import MyService

async with db_manager.async_session() as session:
    my_service = MyService(session)
    result = await my_service.do_something()
```

---

### Добавить миграцию БД

```bash
# 1. Отредактировать модель в src/database/models.py

# 2. Создать миграцию (если используется Alembic)
alembic revision --autogenerate -m "Add new column"

# 3. Применить
alembic upgrade head
```

---

## Debugging

### Print debugging

```python
# Добавить в код
logger.debug(f"Variable: {variable}")

# Запустить с DEBUG логированием
LOG_LEVEL=DEBUG python -m src.bot
```

### Python Debugger

```python
# Добавить в код
import pdb; pdb.set_trace()

# Запустить и взаимодействовать с debugger
python -m src.bot
```

### IDE Debugging

#### VS Code

Создать `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Bot",
      "type": "python",
      "request": "launch",
      "module": "src.bot",
      "justMyCode": true,
      "env": { "PYTHONPATH": "${workspaceFolder}" }
    }
  ]
}
```

Нажать F5 для запуска.

#### PyCharm

1. Right-click на `src/bot.py`
2. Select "Debug 'bot.py'"

---

## Testing

### Написать unit тест

```python
@pytest.mark.asyncio
async def test_something(db_session):
    """Test something."""
    # Arrange - подготовить данные
    pool = DutyPool(group_id=-123, group_title="Test")
    db_session.add(pool)
    await db_session.commit()

    # Act - выполнить операцию
    duty_manager = DutyManager(db_session)
    result = await duty_manager.select_random_duty(pool.id)

    # Assert - проверить результат
    assert result is not None
    assert "user_id" in result
```

### Запустить тесты

```bash
# Все
pytest

# Специфичный файл
pytest tests/unit/test_duty_manager.py

# Специфичный тест
pytest tests/unit/test_duty_manager.py::test_select_random_duty_single_user

# С отчётом
pytest --cov=src

# С verbose выводом
pytest -v

# С print output
pytest -s
```

### Fixtures

Использовать готовые fixtures из `tests/conftest.py`:

```python
@pytest.mark.asyncio
async def test_my_thing(db_session, sample_user_data):
    # db_session - готовая БД сессия
    # sample_user_data - тестовые данные пользователя
    pass
```

---

## Code Quality

### Linting с Ruff

```bash
# Проверить
ruff check src/

# Автофиксить
ruff check --fix src/
```

### Formatting с Black

```bash
# Форматировать
black src/

# Проверить (не менять)
black --check src/
```

### Type checking с mypy

```bash
# Проверить типы
mypy src/

# Strict mode
mypy --strict src/
```

### All checks script

Создать `check-code.sh`:

```bash
#!/bin/bash
set -e

echo "Running ruff..."
ruff check src/

echo "Running black..."
black --check src/

echo "Running mypy..."
mypy src/

echo "Running pytest..."
pytest

echo "✅ All checks passed!"
```

Использовать:

```bash
chmod +x check-code.sh
./check-code.sh
```

---

## Database

### Миграции с Alembic

```bash
# Инициализировать (уже готово)
alembic init migrations

# Создать миграцию
alembic revision --autogenerate -m "Description"

# Применить
alembic upgrade head

# Откатить
alembic downgrade -1

# История
alembic current
alembic history
```

### Прямой доступ к БД

```bash
# Подключиться к PostgreSQL
psql -d flexer_senior_db -U postgres

# Полезные команды
\dt                    # List tables
\d table_name          # Describe table
SELECT * FROM users;   # Query
```

---

## Performance

### Профилирование

```python
import asyncio
import time

async def profile_function():
    start = time.time()

    # Function to profile
    result = await some_function()

    end = time.time()
    print(f"Took {end - start:.2f}s")

asyncio.run(profile_function())
```

### Database Query Analysis

```python
# Включить echo в engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Посмотрит все SQL запросы
)
```

---

## Deployment

### Local Production-like

```bash
# Запустить как production
ENVIRONMENT=production LOG_LEVEL=INFO python -m src.bot
```

### Docker Development

```bash
# Пересобрать образ
docker-compose build

# Запустить
docker-compose up

# Посмотреть логи
docker-compose logs -f bot

# Остановить
docker-compose down
```

### Production Checklist

- [ ] BOT_TOKEN установлен
- [ ] DATABASE_URL указывает на production БД
- [ ] LOG_LEVEL=INFO (не DEBUG)
- [ ] ENVIRONMENT=production
- [ ] Резервные копии БД настроены
- [ ] Мониторинг настроен
- [ ] SSL сертификат для webhook (если используется)

---

## Git Workflow

### Основные команды

```bash
# Посмотреть статус
git status

# Посмотреть изменения
git diff

# Добавить файлы
git add .  # все
git add src/  # папку
git add src/file.py  # файл

# Коммит
git commit -m "feat: description"

# Посмотреть логи
git log --oneline

# Загрузить
git push

# Загрузить branch
git push origin my-branch

# Обновить с main
git pull origin main
```

### Commit messages

Использовать conventional commits:

```
feat: add new feature           # Новая функция
fix: fix bug in handler         # Исправление ошибки
docs: update README             # Документация
style: reformat code            # Форматирование
refactor: restructure code      # Рефакторинг
test: add tests                 # Тесты
chore: update deps              # Зависимости
```

---

## Troubleshooting

### "ImportError: No module named 'aiogram'"

```bash
# Решение: переустановить зависимости
pip install -e ".[dev,db]"
```

### "asyncio event loop already running"

```python
# Решение: использовать pytest-asyncio
@pytest.mark.asyncio
async def test_async():
    pass
```

### "Database connection failed"

```bash
# Проверить что база данных существует
ls -la flexer_senior.db

# Проверить DATABASE_URL в .env
echo $DATABASE_URL

# Если нужно переинициализировать БД, удалите файл и перезапустите
rm flexer_senior.db
python -m src.bot
```

---

## Resources

- [aiogram Docs](https://docs.aiogram.dev/)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
- [asyncio Tutorial](https://docs.python.org/3/library/asyncio.html)
- [pytest Documentation](https://docs.pytest.org/)
- [Pydantic Docs](https://docs.pydantic.dev/)

---

## Support

Есть вопросы?

1. Посмотрите в README.md
2. Посмотрите примеры в src/
3. Запустите тесты: `pytest -v`
4. Создайте Issue на GitHub

---

**Happy Coding! 🚀**
