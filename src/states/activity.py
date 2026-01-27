"""Activity states for FSM."""

from aiogram.fsm.state import State, StatesGroup


class ActivityStates(StatesGroup):
    """States for activity input flow."""

    waiting_for_activity = State()
