from aiogram import Router, F, Bot
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from bot.models import ImageGenerationRequest
from bot.handlers.filters import AdminFilter, is_admin
from database.db import async_session
from videogeneration.sdapi_cleared import AsyncSDClient, save_images
from bot.scheduler import send_photos_group
from bot.handlers.keyboards import BTN_GENERATE, user_main_kb

# Текстовые константы
TXT_START_GENERATION = "Введите описание для генерации изображения:"
TXT_CHOOSE_PARAMS = "Настройте параметры:"
TXT_CHOOSE_SIZE = "Выберите размер изображения:"
TXT_SET_QUANTITY = "Введите количество изображений (от 1 до 100):"
TXT_SET_STEPS = "Введите количество шагов (1-150):"
TXT_SET_CFG = "Введите значение CFG Scale (1-30):"
TXT_SET_SAMPLER = "Введите название сэмплера:"
TXT_SET_NEGATIVE = "Введите отрицательный промпт:"
TXT_SET_FACES = "Восстановление лиц:"
TXT_SIZE_SET = "Установлен размер: {}"
TXT_QUANTITY_SET = "Установлено количество: {}"
TXT_STEPS_SET = "Установлено шагов: {}"
TXT_CFG_SET = "Установлен CFG Scale: {}"
TXT_SAMPLER_SET = "Установлен сэмплер: {}"
TXT_NEGATIVE_SET = "Установлен отрицательный промпт: {}"
TXT_FACES_ENABLED = "Восстановление лиц включено ✅"
TXT_FACES_DISABLED = "Восстановление лиц выключено ❌"
TXT_GENERATION_START = "🚀 Начинаю генерацию с параметрами:\n{}"
TXT_CANCEL = "Генерация отменена"

BTN_SIZE = "📐 Размер"
BTN_QUANTITY = "🔢 Количество"
BTN_GENERATE2 = "🚀 Сгенерировать!"
BTN_STEPS = "📉 Шаги"
BTN_CFG = "⚖️ CFG Scale"
BTN_SAMPLER = "🎛 Сэмплер"
BTN_NEGATIVE = "🚫 Отрицательный"
BTN_FACES = "👥 Лица"
BTN_BACK = "↩️ Назад"
BTN_ENABLE = "✅ Включить"
BTN_DISABLE = "❌ Выключить"

DEFAULT_NEGATIVE = "low quality, deformed, blurry"

# Создаем роутер для генерации изображений
image_router = Router()
image_router.message.filter(AdminFilter())


# Состояния FSM
class GenerationStates(StatesGroup):
    waiting_prompt = State()
    choosing_parameters = State()
    setting_size = State()
    setting_quantity = State()
    setting_steps = State()
    setting_cfg = State()
    setting_sampler = State()
    setting_negative = State()
    setting_faces = State()


# Клавиатуры
def parameters_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SIZE), KeyboardButton(text=BTN_QUANTITY)],
            [KeyboardButton(text=BTN_STEPS), KeyboardButton(text=BTN_CFG)],
            [KeyboardButton(text=BTN_SAMPLER), KeyboardButton(text=BTN_NEGATIVE)],
            [KeyboardButton(text=BTN_FACES)],
            [KeyboardButton(text=BTN_GENERATE2)]
        ],
        resize_keyboard=True
    )


def size_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="512x512"), KeyboardButton(text="768x768")],
            [KeyboardButton(text="1024x1024"), KeyboardButton(text=BTN_BACK)]
        ],
        resize_keyboard=True
    )


def faces_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ENABLE), KeyboardButton(text=BTN_DISABLE)],
            [KeyboardButton(text=BTN_BACK)]
        ],
        resize_keyboard=True
    )


# Хендлеры
@image_router.message(Command("generate"))
@image_router.message(F.text.lower() == "генерация")
@image_router.message(F.text == BTN_GENERATE)
async def cmd_generate(message: Message, state: FSMContext):
    await message.answer(TXT_START_GENERATION)
    await state.set_state(GenerationStates.waiting_prompt)


@image_router.message(GenerationStates.waiting_prompt)
async def process_prompt(message: Message, state: FSMContext):
    await state.update_data(prompt=message.text)
    await state.update_data(params={
        "negative_prompt": DEFAULT_NEGATIVE,
        "steps": 25,
        "width": 512,
        "height": 768,
        "cfg_scale": 7.5,
        "sampler_name": "DPM++ 2M Karras",
        "scheduler": "Karras",
        "seed": -1,
        "n_iter": 1,
        "batch_size": 1,
        "restore_faces": False,
    })
    await message.answer(TXT_CHOOSE_PARAMS, reply_markup=parameters_keyboard())
    await state.set_state(GenerationStates.choosing_parameters)


# Обработчики параметров
@image_router.message(GenerationStates.choosing_parameters, F.text == BTN_SIZE)
async def select_size(message: Message, state: FSMContext):
    await message.answer(TXT_CHOOSE_SIZE, reply_markup=size_keyboard())
    await state.set_state(GenerationStates.setting_size)


@image_router.message(GenerationStates.choosing_parameters, F.text == BTN_QUANTITY)
async def select_quantity(message: Message, state: FSMContext):
    await message.answer(TXT_SET_QUANTITY)
    await state.set_state(GenerationStates.setting_quantity)


@image_router.message(GenerationStates.choosing_parameters, F.text == BTN_STEPS)
async def select_steps(message: Message, state: FSMContext):
    await message.answer(TXT_SET_STEPS)
    await state.set_state(GenerationStates.setting_steps)


@image_router.message(GenerationStates.choosing_parameters, F.text == BTN_CFG)
async def select_cfg(message: Message, state: FSMContext):
    await message.answer(TXT_SET_CFG)
    await state.set_state(GenerationStates.setting_cfg)


@image_router.message(GenerationStates.choosing_parameters, F.text == BTN_SAMPLER)
async def select_sampler(message: Message, state: FSMContext):
    await message.answer(TXT_SET_SAMPLER)
    await state.set_state(GenerationStates.setting_sampler)


@image_router.message(GenerationStates.choosing_parameters, F.text == BTN_NEGATIVE)
async def select_negative(message: Message, state: FSMContext):
    await message.answer(TXT_SET_NEGATIVE)
    await state.set_state(GenerationStates.setting_negative)


@image_router.message(GenerationStates.choosing_parameters, F.text == BTN_FACES)
async def select_faces(message: Message, state: FSMContext):
    await message.answer(TXT_SET_FACES, reply_markup=faces_keyboard())
    await state.set_state(GenerationStates.setting_faces)


# Обработчики установки значений
@image_router.message(GenerationStates.setting_size, F.text.in_(["512x512", "768x768", "1024x1024"]))
async def set_size(message: Message, state: FSMContext):
    width, height = map(int, message.text.split('x'))
    data = await state.get_data()
    data['params']['width'] = width
    data['params']['height'] = height
    await state.update_data(data)
    await message.answer(TXT_SIZE_SET.format(message.text), reply_markup=parameters_keyboard())
    await state.set_state(GenerationStates.choosing_parameters)


@image_router.message(GenerationStates.setting_quantity, F.text.regexp(r'^\d+$').as_('digits'))
async def set_quantity(message: Message, state: FSMContext, digits: F.regexp):
    quantity = int(message.text)
    if 1 <= quantity <= 100:
        data = await state.get_data()
        data['params']['n_iter'] = quantity
        await state.update_data(data)
        await message.answer(TXT_QUANTITY_SET.format(quantity), reply_markup=parameters_keyboard())
        await state.set_state(GenerationStates.choosing_parameters)
    else:
        await message.answer("Некорректное значение! Введите число от 1 до 100")


@image_router.message(GenerationStates.setting_steps, F.text.regexp(r'^\d+$').as_('digits'))
async def set_steps(message: Message, state: FSMContext, digits: F.regexp):
    steps = int(message.text)
    if 1 <= steps <= 150:
        data = await state.get_data()
        data['params']['steps'] = steps
        await state.update_data(data)
        await message.answer(TXT_STEPS_SET.format(steps), reply_markup=parameters_keyboard())
        await state.set_state(GenerationStates.choosing_parameters)
    else:
        await message.answer("Некорректное значение! Введите число от 1 до 150")


@image_router.message(GenerationStates.setting_cfg, F.text.regexp(r'^[\d.]+$').as_('number'))
async def set_cfg(message: Message, state: FSMContext, number: F.regexp):
    cfg = float(message.text)
    if 1 <= cfg <= 30:
        data = await state.get_data()
        data['params']['cfg_scale'] = cfg
        await state.update_data(data)
        await message.answer(TXT_CFG_SET.format(cfg), reply_markup=parameters_keyboard())
        await state.set_state(GenerationStates.choosing_parameters)
    else:
        await message.answer("Некорректное значение! Введите число от 1 до 30")


@image_router.message(GenerationStates.setting_sampler)
async def set_sampler(message: Message, state: FSMContext):
    data = await state.get_data()
    data['params']['sampler_name'] = message.text
    await state.update_data(data)
    await message.answer(TXT_SAMPLER_SET.format(message.text), reply_markup=parameters_keyboard())
    await state.set_state(GenerationStates.choosing_parameters)


@image_router.message(GenerationStates.setting_negative)
async def set_negative(message: Message, state: FSMContext):
    data = await state.get_data()
    data['params']['negative_prompt'] = message.text
    await state.update_data(data)
    await message.answer(TXT_NEGATIVE_SET.format(message.text), reply_markup=parameters_keyboard())
    await state.set_state(GenerationStates.choosing_parameters)


@image_router.message(GenerationStates.setting_faces, F.text.in_([BTN_ENABLE, BTN_DISABLE]))
async def set_faces(message: Message, state: FSMContext):
    restore_faces = message.text == BTN_ENABLE
    data = await state.get_data()
    data['params']['restore_faces'] = restore_faces
    await state.update_data(data)
    status = TXT_FACES_ENABLED if restore_faces else TXT_FACES_DISABLED
    await message.answer(status, reply_markup=parameters_keyboard())
    await state.set_state(GenerationStates.choosing_parameters)


@image_router.message(GenerationStates.choosing_parameters, F.text == BTN_GENERATE2)
async def process_generation(message: Message, bot: Bot, state: FSMContext):
    data = await state.get_data()

    request = ImageGenerationRequest(
        prompt=data['prompt'],
        width=data['params']['width'],
        height=data['params']['height'],
        n_iter=data['params']['n_iter'],
        user_id=message.from_user.id
    )

    async with async_session.begin() as session:
        session.add(request)
        await session.commit()

    api_params = {
        "prompt": data['prompt'],
        **data['params']
    }

    await message.answer(TXT_GENERATION_START.format(api_params), reply_markup=ReplyKeyboardRemove())

    async with AsyncSDClient() as sd:
        await sd.initialize()
        if not any(s["name"] == api_params["sampler_name"] for s in sd.samplers):
            api_params["sampler_name"] = sd.samplers[0]["name"]
            logger.warning("Using fallback sampler: {}", api_params["sampler_name"])

        images = await sd.txt2img(**api_params)
        paths = await save_images(images, "output/generated")
        await send_photos_group(bot, message.from_user.id, paths)

    show_admin_buttons = await is_admin(message.from_user.id)
    await message.answer("Получай сгенерированные изображения. Что ты хочешь сделать дальше?", reply_markup=user_main_kb(show_admin_buttons))

    await state.clear()


# Обработчики возврата и отмены
@image_router.message(
    F.text.in_([BTN_BACK, "отмена"]),
    StateFilter(
        GenerationStates.setting_size,
        GenerationStates.setting_quantity,
        GenerationStates.setting_steps,
        GenerationStates.setting_cfg,
        GenerationStates.setting_sampler,
        GenerationStates.setting_negative,
        GenerationStates.setting_faces
    )
)
async def back_to_parameters(message: Message, state: FSMContext):
    await message.answer(TXT_CHOOSE_PARAMS, reply_markup=parameters_keyboard())
    await state.set_state(GenerationStates.choosing_parameters)


@image_router.message(Command("cancel"), StateFilter("*"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(TXT_CANCEL, reply_markup=ReplyKeyboardRemove())