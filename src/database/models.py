"""Database models for the application."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class DutyStatus(enum.Enum):
    """Duty assignment status."""

    PENDING = "pending"  # Ожидает подтверждения
    CONFIRMED = "confirmed"  # Подтверждено
    DECLINED = "declined"  # Отказался
    SKIPPED = "skipped"  # Пропущено (не ответил)


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )


class TelegramUser(Base):
    """Represents a Telegram user."""

    __tablename__ = "telegram_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(32), nullable=True)
    first_name: Mapped[str] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Relationships
    user_pools: Mapped[list["UserInPool"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    duties: Mapped[list["DutyAssignment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<TelegramUser(user_id={self.user_id}, username={self.username})>"


class DutyPool(Base):
    """Represents a group's duty rotation pool."""

    __tablename__ = "duty_pools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    group_title: Mapped[str] = mapped_column(String(255))
    current_cycle: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Relationships
    users: Mapped[list["UserInPool"]] = relationship(
        back_populates="pool", cascade="all, delete-orphan"
    )
    duty_assignments: Mapped[list["DutyAssignment"]] = relationship(
        back_populates="pool", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<DutyPool(group_id={self.group_id}, title={self.group_title})>"


class UserInPool(Base):
    """Junction table: Users in duty pools."""

    __tablename__ = "users_in_pools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("telegram_users.user_id"))
    pool_id: Mapped[int] = mapped_column(Integer, ForeignKey("duty_pools.id"))
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    has_completed_cycle: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Relationships
    user: Mapped[TelegramUser] = relationship(back_populates="user_pools")
    pool: Mapped[DutyPool] = relationship(back_populates="users")

    def __repr__(self) -> str:
        return f"<UserInPool(user_id={self.user_id}, pool_id={self.pool_id})>"


class DutyAssignment(Base):
    """Represents a duty assignment for a user."""

    __tablename__ = "duty_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("telegram_users.user_id"))
    pool_id: Mapped[int] = mapped_column(Integer, ForeignKey("duty_pools.id"))
    week_number: Mapped[int] = mapped_column(Integer, index=True)  # ISO week number
    assignment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    cycle_number: Mapped[int] = mapped_column(Integer, default=1, index=True)
    message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[DutyStatus] = mapped_column(
        Enum(DutyStatus), default=DutyStatus.PENDING, nullable=False, index=True
    )

    # Activity details (set by confirmed duty)
    activity_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    activity_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    activity_datetime: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    activity_set_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped[TelegramUser] = relationship(back_populates="duties")
    pool: Mapped[DutyPool] = relationship(back_populates="duty_assignments")

    def __repr__(self) -> str:
        return f"<DutyAssignment(user_id={self.user_id}, week={self.week_number}, status={self.status.value})>"
