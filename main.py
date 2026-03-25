cat > main.py << 'EOF'
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from states import DoctorConsultation
from services.ai_service import get_ai_advice

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    await message.answer(
        "Здравствуйте! Я ваш виртуальный медицинский помощник.\n"
        "Я не ставлю диагнозы, но могу проанализировать симптомы.\n\n"
        "Введите ваш возраст (полных лет):"
    )
    await state.set_state(DoctorConsultation.age)

@dp.message(DoctorConsultation.age)
async def process_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите возраст цифрами.")
        return
    await state.update_data(age=int(message.text))
    await message.answer("Укажите ваш пол (М/Ж):")
    await state.set_state(DoctorConsultation.gender)

@dp.message(DoctorConsultation.gender)
async def process_gender(message: Message, state: FSMContext):
    gender = message.text.upper()
    if gender not in ['М', 'Ж', 'M', 'F']:
        await message.answer("Пожалуйста, введите 'М' или 'Ж'.")
        return
    await state.update_data(gender=gender)
    await message.answer("Опишите ваши симптомы:")
    await state.set_state(DoctorConsultation.symptoms)

@dp.message(DoctorConsultation.symptoms)
async def process_symptoms(message: Message, state: FSMContext):
    symptoms = message.text
    user_data = await state.get_data()
    
    await message.answer("🧑‍⚕️ Анализирую...")
    advice = await get_ai_advice(user_data, symptoms)
    await message.answer(advice)
    
    await state.clear()
    await message.answer("Новая консультация - /start")

async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
EOF
