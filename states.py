from aiogram.fsm.state import StatesGroup, State

class DoctorConsultation(StatesGroup):
    age = State()           # состояние ожидания возраста
    gender = State()        # состояние ожидания пола
    conversation = State()  # состояние непрерывного диалога