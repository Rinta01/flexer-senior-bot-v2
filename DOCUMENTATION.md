# Флексер старший - Полная документация

![Python](https://img.shields.io/badge/Python-3.12+-blue)
![aiogram](https://img.shields.io/badge/aiogram-3.24+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Tests](https://img.shields.io/badge/Tests-55_passing-success)

> Умный Telegram-бот для управления ротацией "дежурных" в дружеских группах.  
> Ручное назначение дежурных, система подтверждений, управление активностями и полный цикл без повторений.

**Дата последнего обновления:** 22 января 2026  
**Версия:** 2.0  
**Статус:** ✅ Production Ready

---

## 📋 Содержание

- [Основные возможности](#-основные-возможности)
- [Установка и запуск](#-установка-и-запуск)
- [Команды бота](#-команды-бота)
- [Система активностей](#-система-активностей)
- [Система подтверждений](#-система-подтверждений)
- [Архитектура](#️-архитектура)
- [Разработка](#️-разработка)
- [Тестирование](#-тестирование)
- [Deployment](#-deployment)

---

## 🎯 Основные возможности

### Управление дежурными

- ✅ **Ручное назначение** - `/pick` (случайный выбор) и `/force_pick` (конкретный пользователь через кнопки)
- ✅ **Умная логика** - `/pick` только для свободных недель, `/force_pick` с подтверждением замены
- ✅ **Система подтверждений** - Дежурный принимает или отказывается через inline-кнопки
- ✅ **Умная ротация** - Гарантия отсутствия повторений в текущем цикле
- ✅ **Статусы дежурных** - PENDING (ожидает), CONFIRMED (подтвержден), SKIPPED (отказался)
- ✅ **История** - Просмотр последних 10 назначений через `/history`
- ✅ **Планирование** - Назначение дежурных на несколько недель вперед

### Управление активностями

- ✅ **Установка мероприятий** - Дежурный может добавить активность на неделю
- ✅ **Безопасность** - Только подтвержденный дежурный текущей недели может устанавливать
- ✅ **Гибкие форматы** - Поддержка разных форматов даты и времени
- ✅ **Информативность** - Отображение дежурного и активности через `/activity`

### Технические возможности

- ✅ **Масштабируемость** - Поддержка нескольких групп одновременно
- ✅ **Async/await** - Полностью асинхронная архитектура
- ✅ **Тестирование** - 55+ unit и интеграционных тестов
- ✅ **Интерактивность** - Inline-клавиатуры для выбора недель

---

## 🚀 Установка и запуск

### Требования

- **Python 3.12+**
- **SQLite 3+** (уже установлен на macOS и Linux)
- **Telegram бот токен** от [@BotFather](https://t.me/botfather)

### Вариант 1: Локальный запуск

```bash
# 1. Клонировать репозиторий
git clone https://github.com/Rinta01/flexer-senior-bot-v2.git
cd flexer-senior-bot-v2

# 2. Создать виртуальное окружение
python3.12 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# 3. Установить зависимости
pip install -e ".[dev,db]"

# 4. Настроить конфигурацию
cp .env.example .env
# Отредактировать .env и установить BOT_TOKEN

# 5. Запустить бота
python -m src.bot
```

### Вариант 2: Docker Compose (рекомендуется)

```bash
# 1. Настроить .env
cp .env.example .env
# Установить BOT_TOKEN в .env

# 2. Запустить
docker-compose up -d

# 3. Проверить логи
docker-compose logs -f bot

# 4. Остановить
docker-compose down
```

### Конфигурация (.env)

```env
# Обязательные параметры
BOT_TOKEN=your_telegram_bot_token_from_botfather

# База данных (SQLite по умолчанию)
DATABASE_URL=sqlite+aiosqlite:///./flexer_senior.db

# Расписание автоматического выбора
WEEKLY_DUTY_ENABLED=true  # true/false
WEEKLY_DUTY_DAY=6         # 0=Понедельник, 6=Воскресенье
WEEKLY_DUTY_TIME=15:00    # Всегда UTC+3

# Логирование
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### Добавление бота в группу

1. Создайте или откройте Telegram группу
2. Добавьте вашего бота в группу (найдите по username)
3. (Опционально) Дайте боту права администратора
4. Отправьте `/start` для проверки
5. Участники могут присоединиться через `/join`

---

## 📖 Команды бота

### Команды управления пулом

| Команда  | Описание                        | Где работает  |
| -------- | ------------------------------- | ------------- |
| `/start` | Показать приветствие            | Везде         |
| `/help`  | Полная справка по всем командам | Везде         |
| `/join`  | Присоединиться к пулу дежурных  | Только группы |
| `/leave` | Выйти из пула дежурных          | Только группы |
| `/pool`  | Показать список участников пула | Только группы |

**Примеры:**

```
/join
→ ✅ Вы присоединились к пулу дежурных!
→ 👥 Участников в пуле: 5

/pool
→ 👥 Список участников пула (5):
→ 1. Иван Петров (@ivan) ✅
→ 2. Мария Сидорова (@maria) ✅
...
```

### Команды управления дежурствами

| Команда                 | Описание                                                         | Кто может использовать |
| ----------------------- | ---------------------------------------------------------------- | ---------------------- |
| `/pick`                 | Выбрать дежурного случайно (только для свободных недель)         | Все в группе           |
| `/force_pick`           | Назначить конкретного пользователя (с подтверждением при замене) | Все в группе           |
| `/auto_pick`            | Показать/изменить авто-выбор для текущей группы                  | Все в группе           |
| `/activity`             | Показать дежурного и активность для выбранной недели             | Все в группе           |
| `/history`              | Показать последние 10 записей о дежурствах                       | Все в группе           |

**Примеры:**

```
/pick
→ Выбор недели через кнопки
→ 🎯 Дежурный на неделю 27 января - 2 февраля
→ Поздравляем, @ivan! 🎉

/force_pick
→ Выбор участника через кнопки
→ Выбор недели через кнопки
→ ⚠️ На эту неделю уже назначен дежурный: @ivan (статус: ⏳ Ожидает подтверждения)
→ [Да, заменить] [Отмена]

/force_pick @maria
→ Быстрый вариант: сразу выбор недели для @maria

/auto_pick
→ Показывает текущий статус авто-выбора для группы

/auto_pick off
→ Отключает автоматический выбор для группы

/activity
→ Выбор недели через кнопки
→ 🎯 Дежурный недели
→ Неделя: 27 января - 2 февраля
→ Дежурный: @ivan
→ Статус: ✅ Подтверждено
```

### Команды для активностей

| Команда         | Описание                         | Кто может использовать                        |
| --------------- | -------------------------------- | --------------------------------------------- |
| `/set_activity` | Установить мероприятие на неделю | Только подтвержденный дежурный текущей недели |

**Пример:**

```
/set_activity
→ Выбор недели через кнопки
→ Бот: "✅ Ответьте на это сообщение (через Reply) с деталями"
→ Пользователь отвечает через Reply:

Игра в мафию
Играем в кафе Пушкин
28.01 19:30

→ ✅ Активность установлена!
```

---

## 🎯 Система активностей

### Обзор

Дежурный недели может установить мероприятие для всей группы. **Только подтвержденный дежурный текущей недели** имеет право устанавливать активность.

### Установка активности

**Шаги:**

1. Отправьте команду `/set_activity`
2. Выберите неделю из предложенных кнопок
3. **Ответьте (Reply) на сообщение бота** с деталями мероприятия в многострочном формате

**Формат ввода (многострочный):**

```
Название
Описание (необязательно)
28.01 19:30 (необязательно)
```

**Примеры ввода:**

```
Игра в мафию
Играем в кафе Пушкин
28.01 19:30

Боулинг
Встречаемся в "Космик"
02.02 18:00

Кино
15.01.2026 20:30

Настольные игры
(без даты и времени)
```

**Поддерживаемые форматы:**

- **Дата:** `28.01` (текущий год), `28.01.2026` (с годом), `28-01`, `28-01-2026`
- **Время:** `19:30`, `19-30`

**Проверки безопасности:**

1. ✅ Команда работает только в групповых чатах
2. ✅ Существует пул дежурных для группы
3. ✅ Есть подтвержденный дежурный на выбранную неделю
4. ✅ **Пользователь - тот, кто инициировал команду**
5. ✅ **Сообщение является ответом (Reply) на prompt бота**
6. ✅ Все обязательные поля (название) заполнены корректно

### Просмотр активности

Команда `/activity` показывает информацию о дежурном и запланированной активности.

### Просмотр активности

Команда `/activity` показывает информацию о дежурном и запланированной активности.

**Пример с активностью:**

```
🎯 Дежурный недели

Неделя: 27 января - 2 февраля
Дежурный: @username
Статус: ✅ Подтверждено

📅 Активность недели:
Название: Игра в мафию
Описание: Играем в кафе Пушкин
Когда: 28.01.2026 в 19:30

До встречи, не теряемся 💪
```

**Пример без активности (дежурный подтвержден):**

```
🎯 Дежурный недели

Неделя: 27 января - 2 февраля
Дежурный: @username
Статус: ✅ Подтверждено

❓ Активность пока не установлена.

💡 @username, вы можете добавить информацию о мероприятии:
/set_activity Название | Описание | Дата | Время
```

**Пример с ожиданием подтверждения:**

```
🎯 Дежурный недели

Неделя: 27 января - 2 февраля
Дежурный: @username
Статус: ⏳ Ожидает подтверждения

❓ Активность пока не установлена.

⏳ Ожидаем подтверждения от дежурного.
```

---

## ✅ Система подтверждений

### Статусы дежурства

| Статус      | Эмодзи | Описание                             |
| ----------- | ------ | ------------------------------------ |
| `PENDING`   | ⏳     | Ожидает подтверждения                |
| `CONFIRMED` | ✅     | Дежурный подтвердил назначение       |
| `DECLINED`  | ❌     | Дежурный отказался (не используется) |
| `SKIPPED`   | ⏭️     | Дежурство пропущено/отменено         |

### Процесс подтверждения

**1. Объявление дежурного**

Когда бот выбирает дежурного (через `/pick` или `/force_pick`):

```
🎯 Дежурный на неделю 27 января - 2 февраля

Поздравляем, @username! 🎉

Ты выбран дежурным на эту неделю и отвечаешь за организацию
мероприятия для группы.

Пожалуйста, подтверди или откажись:

[✅ Принять дежурство]  [❌ Отказаться]
```

**2. Подтверждение (✅ Принять)**

- Только назначенный пользователь может нажать кнопку
- Статус меняется на `CONFIRMED`
- Дежурный может установить активность

```
🎯 Дежурный на неделю 27 января - 2 февраля

@username принял дежурство! ✅

Все замерли в ожидании анонса активности 🫠
```

**3. Отказ (❌ Отказаться)**

- Статус меняется на `SKIPPED`
- Дежурство помечается как пропущенное
- Неделя становится свободной для нового назначения

```
🎯 Дежурный на неделю 27 января - 2 февраля

@username отказался от дежурства ❌

Дежурство будет пропущено.
```

---

## 🏗️ Архитектура

### Структура проекта

```
flexer-senior-v2/
├── src/
│   ├── bot.py                    # 🚀 Точка входа, регистрация handlers
│   ├── config.py                 # ⚙️ Конфигурация из .env
│   │
│   ├── handlers/                 # 📥 Обработчики команд (aiogram routers)
│   │   ├── start.py, help.py     # Информационные команды
│   │   ├── join.py, leave.py     # Управление пулом
│   │   ├── pool.py               # Просмотр участников
│   │   ├── pick.py               # Случайный выбор дежурного
│   │   ├── force_pick.py         # Назначение конкретного пользователя
│   │   ├── activity.py           # Активности (/activity, /set_activity)
│   │   ├── history.py            # История дежурств
│   │   ├── duty_callbacks.py     # ✅❌ Обработка inline-кнопок подтверждения
│   │   └── week_selection.py     # Обработка выбора недели
│   │
│   ├── services/                 # 🎯 Бизнес-логика
│   │   ├── duty_manager.py       # Управление дежурствами и ротацией
│   │   ├── duty_selector.py      # Логика выбора дежурного
│   │   ├── user_manager.py       # Управление пулом пользователей
│   │   └── notification.py       # Отправка уведомлений
│   │
│   ├── database/                 # 🗄️ Слой данных (SQLAlchemy async)
│   │   ├── engine.py             # Управление БД, сессии
│   │   ├── models.py             # ORM модели
│   │   └── repositories.py       # CRUD операции
│   │
│   ├── keyboards/                # ⌨️ Inline клавиатуры
│   │   └── week_selector.py      # Клавиатуры выбора недели
│   │
│   ├── middlewares/              # 🔀 Middlewares
│   │   └── logging.py            # Логирование всех событий
│   │
│   └── utils/                    # 🛠️ Утилиты
│       ├── logger.py             # Настройка логирования
│       ├── validators.py         # Валидация
│       └── formatters.py         # Форматирование дат, сообщений, статусов
│
├── tests/                        # 🧪 Тесты (pytest)
│   ├── conftest.py               # Фикстуры
│   ├── unit/                     # Unit-тесты (55 тестов)
│   └── integration/              # Интеграционные тесты
│
├── docker-compose.yml            # 🐳 Docker конфигурация
├── Dockerfile                    # 🐳 Docker образ
├── pyproject.toml                # 📦 Зависимости
└── pytest.ini                    # 🧪 Конфигурация pytest
```

### Принципы архитектуры

**Clean Architecture:**

```
User Command → Handlers → Services → Repositories → Database
                  ↓
           (async/await)
```

**Разделение ответственности:**

- **Handlers** - прием команд, валидация контекста, отправка ответов
- **Services** - бизнес-логика, оркестрация операций
- **Repositories** - CRUD операции с БД, queries
- **Models** - определение структуры данных (ORM)
- **Utils** - вспомогательные функции (форматирование, валидация)

### Модели данных

#### TelegramUser

```python
- user_id (BigInteger, PK)        # Telegram user ID
- username (String, nullable)     # @username
- first_name (String)             # Имя
- last_name (String, nullable)    # Фамилия
- is_active (Boolean)             # Активен ли
- created_at (DateTime)           # Дата создания
```

#### DutyPool

```python
- id (Integer, PK, autoincrement)
- group_id (BigInteger, unique)   # Telegram chat ID
- title (String)                  # Название группы
- current_cycle (Integer)         # Текущий цикл ротации
- is_active (Boolean)             # Активен ли пул
- auto_pick_enabled (Boolean)     # Включен ли автоматический выбор scheduler-ом
- created_at (DateTime)
```

#### UserInPool

```python
- id (Integer, PK)
- user_id (BigInteger, FK)        # -> TelegramUser
- pool_id (Integer, FK)           # -> DutyPool
- has_completed_cycle (Boolean)   # Завершил ли текущий цикл
- added_at (DateTime)
```

#### DutyAssignment

```python
- id (Integer, PK)
- user_id (BigInteger, FK)        # -> TelegramUser
- pool_id (Integer, FK)           # -> DutyPool
- year (Integer)                  # Год недели (ISO)
- week_number (Integer)           # ISO week (1-53)
- cycle_number (Integer)          # Номер цикла
- assignment_date (DateTime)      # Когда назначен
- status (Enum)                   # PENDING/CONFIRMED/DECLINED/SKIPPED
- notification_sent (Boolean)     # Было ли отправлено уведомление

# Поля активности
- activity_title (String)         # Название мероприятия
- activity_description (Text)     # Описание
- activity_datetime (DateTime)    # Дата и время мероприятия
- activity_set_at (DateTime)      # Когда установлено
```

### Логика выбора дежурного

**Алгоритм:**

1. **Получить пул** активных пользователей для группы
2. **Фильтровать:** выбрать где `has_completed_cycle=False`
3. **Если список пуст:** сбросить флаги для всех → новый цикл
4. **Случайный выбор** из отфильтрованного списка
5. **Пометить:** `has_completed_cycle=True`
6. **Создать DutyAssignment** со статусом `PENDING`
7. **Отправить уведомление** с inline-кнопками

**Пример: 3 пользователя**

```
Цикл 1:  Alice (week 1) → Bob (week 2) → Charlie (week 3)
         [completed]      [completed]     [completed]
         ↓ Все завершили цикл → сброс флагов

Цикл 2:  Bob (week 4) → Charlie (week 5) → Alice (week 6)
```

**Гарантии:**

- ✅ Никто не повторяется в пределах одного цикла
- ✅ Равномерное распределение
- ✅ Автоматический сброс и новый цикл
- ✅ Корректная обработка присоединений/выходов

---

## 🧪 Тестирование

### Запуск тестов

```bash
# Все тесты
pytest

# С подробным выводом
pytest -v

# Только unit-тесты
pytest tests/unit/

# С отчётом покрытия
pytest --cov=src --cov-report=html
open htmlcov/index.html  # macOS
```

### Текущее состояние

- **55 тестов** (все проходят ✅)
- **Покрытие кода:** ~30%
- **Unit-тесты:** 52
- **Интеграционные:** 3

### Структура тестов

```
tests/
├── conftest.py                      # Общие фикстуры
├── unit/
│   ├── test_duty_manager.py         # Логика дежурств
│   ├── test_user_manager.py         # Управление пользователями
│   ├── test_repositories.py         # CRUD операции
│   ├── test_validators.py           # Валидация
│   ├── test_activity_security.py    # Безопасность активностей
│   ├── test_activity_formatters.py  # Форматирование активностей
│   ├── test_duty_callbacks.py       # Обработка подтверждений
│   └── ...
└── integration/
    └── test_handlers.py             # Интеграция handlers
```

---

## 🛠️ Разработка

### Локальная среда разработки

```bash
# 1. Клонировать и подготовить
git clone https://github.com/Rinta01/flexer-senior-bot-v2.git
cd flexer-senior-bot-v2
python3.12 -m venv venv
source venv/bin/activate

# 2. Установить зависимости для разработки
pip install -e ".[dev,db]"

# 3. Настроить .env
cp .env.example .env
# Установить BOT_TOKEN

# 4. Запустить
python -m src.bot
```

### Workflow разработки

**1. Создать feature branch**

```bash
git checkout -b feature/my-feature
# или
git checkout -b fix/bug-description
```

**2. Написать код**

Придерживайтесь существующих паттернов. Пример нового handler:

```python
# src/handlers/my_handler.py
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from src.utils.logger import setup_logging

logger = setup_logging(__name__)
router = Router()

@router.message(Command("mycommand"))
async def my_command_handler(message: Message) -> None:
    """Handle /mycommand."""
    await message.answer("Response")
    logger.info(f"Handled /mycommand from {message.from_user.id}")
```

**3. Написать тесты**

```python
# tests/unit/test_my_handler.py
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_my_command():
    """Test my command handler."""
    message = AsyncMock()
    message.from_user.id = 12345

    await my_command_handler(message)

    message.answer.assert_called_once_with("Response")
```

**4. Запустить тесты**

```bash
pytest tests/unit/test_my_handler.py -v
```

**5. Коммит и push**

```bash
git add .
git commit -m "feat: add my new feature"
git push origin feature/my-feature
```

### Стиль кода

- **Type hints** везде
- **Docstrings** для всех публичных функций
- **Async/await** для всех IO операций
- **f-strings** для форматирования
- Следовать существующим паттернам проекта

---

## 🐳 Deployment

### Docker Compose (рекомендуется)

```bash
# 1. Подготовить .env
cp .env.example .env
# Установить BOT_TOKEN

# 2. Запустить
docker-compose up -d

# 3. Проверить статус
docker-compose ps

# 4. Логи
docker-compose logs -f bot

# 5. Остановить
docker-compose down
```

### Systemd Service (Linux)

**1. Создать service файл:**

```bash
sudo nano /etc/systemd/system/flexer-senior-bot.service
```

**2. Содержимое файла:**

```ini
[Unit]
Description=Flexer Senior Telegram Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/flexer-senior-v2
Environment="PATH=/path/to/flexer-senior-v2/venv/bin"
ExecStart=/path/to/flexer-senior-v2/venv/bin/python -m src.bot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**3. Активировать и запустить:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable flexer-senior-bot
sudo systemctl start flexer-senior-bot

# Проверить статус
sudo systemctl status flexer-senior-bot

# Логи
sudo journalctl -u flexer-senior-bot -f
```

---

## 📚 Дополнительная информация

### Используемые технологии

- **[aiogram 3.24+](https://aiogram.dev/)** - Асинхронный фреймворк для Telegram Bot API
- **[SQLAlchemy 2.0+](https://www.sqlalchemy.org/)** - Async ORM для работы с БД
- **[aiosqlite](https://github.com/omnilib/aiosqlite)** - Асинхронный драйвер для SQLite
- **[pytest](https://pytest.org/)** - Фреймворк для тестирования
- **[APScheduler](https://apscheduler.readthedocs.io/)** - Планировщик задач (опционально)

### История изменений

См. [CHANGELOG.md](CHANGELOG.md) для полной истории изменений.

### Лицензия

MIT License - см. [LICENSE](LICENSE)

### Поддержка

Если у вас возникли вопросы или проблемы:

- 🐛 [Создайте Issue](https://github.com/Rinta01/flexer-senior-bot-v2/issues)
- 📧 Свяжитесь с разработчиком

### Контрибьюция

Мы приветствуем вклад в проект! Пожалуйста:

1. Fork репозитория
2. Создайте feature branch
3. Напишите код с тестами
4. Убедитесь, что все тесты проходят
5. Создайте Pull Request

---

**Спасибо за использование Flexer Senior Bot! 🎉**

1. Проверьте [Issues](https://github.com/Rinta01/flexer-senior-bot-v2/issues)
2. Создайте новый Issue с подробным описанием
3. Или свяжитесь с автором

---

**Разработано с ❤️ для управления дежурными в дружеских группах**
