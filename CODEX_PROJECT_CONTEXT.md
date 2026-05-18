# Codex Project Context

Краткая рабочая памятка по проекту `flexer-senior-v2`.

## Что это

`Флексер старший` - Telegram-бот для управления ротацией дежурных в группах.

Основной сценарий:

- участники входят в пул через `/join` и выходят через `/leave`;
- `/pick` случайно выбирает дежурного на выбранную неделю;
- `/force_pick @username` назначает конкретного пользователя на выбранную неделю;
- выбранный дежурный подтверждает или отклоняет назначение inline-кнопками;
- подтвержденный дежурный может задать активность через `/set_activity`;
- `/activity` показывает дежурного и активность выбранной недели;
- `/history` показывает историю назначений.

Автоматический еженедельный выбор через `APScheduler` в коде остался, но запуск scheduler сейчас отключен в `src/bot.py`; актуальный рабочий режим - ручной выбор через `/pick`.

## Стек

- Python 3.12+
- aiogram 3.x
- SQLAlchemy 2.x async
- SQLite + aiosqlite
- Pydantic Settings
- pytest + pytest-asyncio
- Docker / docker-compose

## Основные файлы

- `src/bot.py` - точка входа, создание `Bot`/`Dispatcher`, регистрация routers, startup/shutdown.
- `src/config.py` - настройки из `.env`.
- `src/database/models.py` - ORM-модели и `DutyStatus`.
- `src/database/repositories.py` - слой доступа к данным.
- `src/database/engine.py` - async engine/session manager.
- `src/services/duty_manager.py` - ключевая бизнес-логика выбора и назначения дежурных.
- `src/services/user_manager.py` - управление участниками пула.
- `src/services/notification.py` - Telegram-уведомления и inline-кнопки подтверждения.
- `src/services/duty_selector.py` - общий flow выбора и объявления дежурного для старого/авто-сценария.
- `src/handlers/` - команды и callback handlers.
- `src/keyboards/week_selector.py` - клавиатура выбора недели и callback data parser.
- `src/utils/calendar.py` - генерация Google Calendar ссылки и хранение location в существующем описании активности.
- `src/utils/formatters.py` - форматирование дат, статусов и упоминаний.
- `tests/` - unit и integration тесты.

## Архитектура

Проект следует простой layered/Clean Architecture схеме:

1. `handlers` принимают Telegram events, валидируют чат/команду и открывают DB session.
2. `services` содержат бизнес-правила.
3. `repositories` инкапсулируют SQLAlchemy-запросы.
4. `models` описывают таблицы.
5. `utils` и `keyboards` держат переиспользуемые чистые функции.

При добавлении новой функциональности лучше сохранять этот рисунок: handler тонкий, бизнес-логика в service, запросы в repository, форматирование отдельно.

## Данные

Ключевые модели:

- `TelegramUser` - пользователь Telegram.
- `DutyPool` - пул дежурных для группы.
- `UserInPool` - связь пользователя с пулом и флаг `has_completed_cycle`.
- `DutyAssignment` - назначение дежурного на ISO-неделю, статус, message id, данные активности.

Статусы `DutyStatus`:

- `PENDING`
- `CONFIRMED`
- `DECLINED`
- `SKIPPED`
- `FORCE_REMOVED`

## Команды разработки

Установка зависимостей:

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -e ".[dev,db]"
```

Запуск бота:

```bash
python -m src.bot
# или
./run.sh start
```

Тесты:

```bash
./venv/bin/pytest tests/ -q
# или
./run.sh test
```

Docker:

```bash
cp .env.example .env
# заполнить BOT_TOKEN
docker-compose up -d
```

## Текущее состояние на момент создания памятки

- Тесты проходили: `73 passed`.
- После отключения Google Calendar ссылки при нераспознанной дате/времени тесты проходили: `91 passed`.
- `git status` был чистым до создания этого файла.
- В README/DOCUMENTATION местами указано `55+` тестов, фактически сейчас больше.
- В README упоминается `LICENSE`, но файл `LICENSE` в корне не был найден.

## Нюансы и потенциальные зоны риска

- В коде есть несколько реализаций/мест работы с ISO-неделями. Каноничная функция для дат недели - `get_week_dates()` в `src/utils/formatters.py`.
- `create_week_selector_keyboard()` использует упрощенный rollover `week_num > 52`; ISO-год иногда имеет 53 недели.
- `format_activity_info()` форматирует диапазон недели без явного `year`, поэтому для будущих/переходных недель стоит быть внимательным.
- Scheduler-код не удален, но в `start_polling()` закомментирован. Если возвращать автоподбор, нужно синхронизировать его с новой логикой выбора конкретной недели.
- FSM для `/set_activity` использует `MemoryStorage`, поэтому состояние ввода активности не переживет рестарт процесса.
- После уточнения активности в `/set_activity` бот отправляет inline-кнопку `Добавить в Google Calendar` с prefill URL только если дата и время успешно распознаны. Формат ввода: 1-я строка название, 2-я описание, 3-я место, 4-я дата/время. Введенное время трактуется как фиксированный chat timezone `UTC+3`; Google URL получает UTC interval.

## Документация

- `README.md` - быстрый обзор.
- `DOCUMENTATION.md` - подробная документация.
- `DOCS_INDEX.md` - навигация по документации.
- `CHANGELOG.md` - история изменений.
- `.github/copilot-instructions.md` - исходное ТЗ/инструкции от предыдущего AI.
