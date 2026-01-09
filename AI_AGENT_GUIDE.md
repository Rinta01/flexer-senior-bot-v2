# 📚 AI Agent Instructions - Flexer Senior Bot v2

This document supplements `.github/copilot-instructions.md` with implementation-specific guidance for AI agents working on this codebase.

## 🎯 Project Status: FULLY IMPLEMENTED

- ✅ 1,905 lines of production code
- ✅ 20+ unit & integration tests
- ✅ Complete documentation
- ✅ Docker setup ready
- ✅ Database models & migrations ready

---

## 🏗️ Architecture Overview

The project follows **Clean Architecture**:

```
User Command → Handlers → Services → Repositories → Database
                ↓
         (async/await)
                ↓
         APScheduler (weekly jobs)
```

**Key principle:** Each layer has a single responsibility and can be tested independently.

---

## 🔑 Critical Files for Understanding

### Must Read First:

1. **[src/bot.py](src/bot.py)** - Application entry point, scheduler setup, router registration
2. **[src/services/duty_manager.py](src/services/duty_manager.py)** - Core rotation logic (read closely!)
3. **[src/database/models.py](src/database/models.py)** - Data model relationships
4. **[README.md](README.md)** - Full user documentation

### For Development:

- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Developer workflow and patterns
- **[QUICKSTART.md](QUICKSTART.md)** - Local setup instructions
- **[tests/conftest.py](tests/conftest.py)** - Test setup and fixtures

---

## 💡 Key Implementation Details

### Duty Selection Logic (Most Complex)

Located in `src/services/duty_manager.py::DutyManager.select_random_duty()`

**The algorithm ensures no user is selected twice in a cycle:**

```python
1. Get pool's active users
2. Filter: users where has_completed_cycle=False
3. If empty: Reset all users' has_completed_cycle to False
4. Random choice from filtered users
5. Mark selected user: has_completed_cycle=True
6. Create DutyAssignment record
7. Announce via NotificationService
```

**Example with 3 users:**

- Cycle 1: Alice → Bob → Charlie (each marked as completed)
- Cycle 2: Reset all, select again: Bob → Charlie → Alice

### Database State Management

**Critical fields for duty rotation:**

```python
UserInPool.has_completed_cycle  # False until selected in current cycle
DutyPool.current_cycle          # Incremented when all users complete
DutyAssignment.week_number      # ISO week (1-53)
DutyAssignment.cycle_number     # Which cycle the assignment belongs to
```

**Query pattern:**

```python
# Get available users for selection
available = await repo.get_users_not_in_cycle(pool_id)
# These have has_completed_cycle=False
```

### Async Everywhere

Everything is `async`:

- Database queries use `aiosqlite` with `SQLAlchemy` async session
- Handlers are async functions
- Services receive `AsyncSession`
- Tests use `@pytest.mark.asyncio`

**Never use synchronous database calls!**

---

## 🎮 Command Handler Pattern

All command handlers follow this pattern:

```python
@router.message(Command("commandname"))
async def command_handler(message: Message) -> None:
    """Handle /commandname."""
    try:
        # Check context (e.g., group chat only)
        if message.chat.id > 0:  # Private chat
            await message.answer("This only works in groups")
            return

        # Get async session
        async with db_manager.async_session() as session:
            service = MyService(session)
            result = await service.do_something()

        # Send response
        await message.answer(result)
        logger.info(f"Handled /commandname from user {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error in command_handler: {e}")
        await message.answer("❌ An error occurred")
```

**Key points:**

- Always wrap in try/except
- Check group context first
- Get session from `db_manager.async_session()`
- Use service layer for logic
- Log operations
- Return user-friendly messages

---

## 🧪 Testing Guidelines

### Test Fixtures (in `tests/conftest.py`)

```python
# Use these in tests:
db_session          # AsyncSession with in-memory SQLite
async_engine        # In-memory test database
sample_user_data    # Dict with: user_id, first_name, username, last_name
sample_group_data   # Dict with: group_id, group_title
```

### Test Pattern

```python
@pytest.mark.asyncio
async def test_something(db_session, sample_user_data):
    # Arrange - Set up test data
    user = TelegramUser(**sample_user_data)
    db_session.add(user)
    await db_session.commit()

    # Act - Execute the thing being tested
    manager = DutyManager(db_session)
    result = await manager.select_random_duty(pool_id)

    # Assert - Verify expectations
    assert result is not None
    assert result["user_id"] == sample_user_data["user_id"]
```

### Run Tests

```bash
pytest                                    # All
pytest tests/unit/test_duty_manager.py  # Specific file
pytest -v -s                             # Verbose with prints
pytest --cov=src --cov-report=html      # Coverage report
```

---

## 📦 Adding New Features

### Example: Add /status command

```python
# 1. Create src/handlers/status.py
from aiogram import Router
from aiogram.types import Message
from src.database.engine import db_manager
from src.services.user_manager import UserManager

router = Router()

@router.message(Command("status"))
async def status_command(message: Message) -> None:
    """Show pool status."""
    try:
        async with db_manager.async_session() as session:
            user_manager = UserManager(session)
            count = await user_manager.get_pool_users_count(message.chat.id)

        response = f"👥 Pool members: {count}"
        await message.answer(response)
        logger.info(f"Showed status for group {message.chat.id}")
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.answer("❌ Error")

# 2. Register in src/bot.py setup_handlers()
from src.handlers import status
self.dp.include_router(status.router)

# 3. Add test tests/unit/test_status.py
@pytest.mark.asyncio
async def test_status_command(db_session, sample_group_data):
    pool = DutyPool(**sample_group_data)
    db_session.add(pool)
    await db_session.commit()

    user_manager = UserManager(db_session)
    count = await user_manager.get_pool_users_count(pool.id)
    assert count == 0
```

---

## 🔧 Common Modifications

### Change weekly duty time

Edit `.env`:

```env
WEEKLY_DUTY_DAY=0      # 0=Monday, 1=Tuesday, etc.
WEEKLY_DUTY_HOUR=14    # 14:00
WEEKLY_DUTY_MINUTE=30
```

### Add a database field

1. Update model in `src/database/models.py`:

```python
class MyModel(Base):
    __tablename__ = "my_table"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    new_field: Mapped[str] = mapped_column(String(100))  # New field
```

2. Update repository if needed in `src/database/repositories.py`

3. Create migration (optional):

```bash
alembic revision --autogenerate -m "Add new_field"
alembic upgrade head
```

### Change notification message

Edit `src/services/notification.py::announce_duty_assignment()`:

```python
message_text = (
    f"🎯 <b>Your Custom Title</b>\n\n"
    f"New text here..."
)
```

---

## ⚡ Performance & Optimization

### Database Query Optimization

Use `await self.session.commit()` carefully:

```python
# Good - one commit at end
user1.field = value1
user2.field = value2
await session.commit()  # Once

# Avoid - multiple commits
user1.field = value1
await session.commit()  # Unnecessary
user2.field = value2
await session.commit()  # Unnecessary
```

### Logging

Use appropriate log levels:

```python
logger.debug("Detailed info for developers")
logger.info("Important events (user joined, duty assigned)")
logger.warning("Something unexpected")
logger.error("Error with full context: {e}")
```

Control via `LOG_LEVEL=DEBUG` env var

---

## 🚀 Deployment Checklist

- [ ] All tests pass: `pytest`
- [ ] Code is formatted: `black src/`
- [ ] No lint issues: `ruff check src/`
- [ ] Types are correct: `mypy src/`
- [ ] `.env` configured with production values
- [ ] BOT_TOKEN is valid
- [ ] DATABASE_URL points to production DB
- [ ] ENVIRONMENT=production
- [ ] LOG_LEVEL=INFO
- [ ] Docker image builds: `docker build -t flexer-bot .`
- [ ] Docker compose works: `docker-compose up`

---

## 🆘 Debugging

### Enable detailed logging

```bash
LOG_LEVEL=DEBUG python -m src.bot
```

### Check database state

```bash
psql -d flexer_senior_db -U postgres
SELECT * FROM telegram_users;
SELECT * FROM duty_assignments;
```

### Run with debugger

Add to code:

```python
import pdb; pdb.set_trace()
```

Run and interact:

```bash
python -m src.bot
# When it hits pdb, type commands like 'n' (next), 'c' (continue), etc.
```

### Check Docker logs

```bash
docker-compose logs -f bot        # Live logs
docker-compose logs bot | tail -20 # Last 20 lines
```

---

## 🎓 Code Style

The project enforces:

- **Black** for formatting (line length: 100)
- **Ruff** for linting (strict rules)
- **Type hints** everywhere
- **Docstrings** for all public functions
- **Logging** instead of print()
- **Async/await** - never blocking calls

---

## 📞 Getting Help

If working on this project:

1. Check [README.md](README.md) - Full user docs
2. Check [DEVELOPMENT.md](DEVELOPMENT.md) - Developer guide
3. Look at existing handlers in `src/handlers/` for patterns
4. Run tests: `pytest -v` to see expected behavior
5. Check test files: `tests/unit/` show all APIs

---

## 🎯 Key Takeaways for AI Agents

1. **Async everything** - No synchronous DB calls
2. **Repository pattern** - Access DB through repos, not directly
3. **Service layer** - Business logic goes in services
4. **Error handling** - Try/except with logging everywhere
5. **Type hints** - Use mypy-compatible types
6. **Tests first** - Write tests for new features
7. **Logging** - Log important operations
8. **Sessions** - Always use `async with db_manager.async_session()`

---

**Version:** 0.1.0  
**Last Updated:** January 9, 2026  
**Status:** Production Ready ✅
