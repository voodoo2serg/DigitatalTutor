"""
DigitalTutor Bot - Keyboards
ReplyKeyboard разметка для бота
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_menu():
    """Главное меню для студентов"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📋 Мои работы"),
                KeyboardButton(text="➕ Сдать работу"),
            ],
            [
                KeyboardButton(text="📊 Статус"),
                KeyboardButton(text="📅 Мой план"),
            ],
            [
                KeyboardButton(text="💬 Написать руководителю"),
                KeyboardButton(text="❓ Помощь"),
            ],
        ],
        resize_keyboard=True
    )


def get_admin_menu():
    """Меню для администратора"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📋 Все работы"),
                KeyboardButton(text="👥 Студенты"),
            ],
            [
                KeyboardButton(text="📊 Статистика системы"),
                KeyboardButton(text="📤 Массовая рассылка"),
            ],
            [
                KeyboardButton(text="🔙 Студенческое меню"),
            ],
        ],
        resize_keyboard=True
    )


def get_cancel_menu():
    """Меню с кнопкой отмены"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )


def get_role_selection_menu():
    """Меню выбора роли при регистрации"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎓 ВКР")],
            [KeyboardButton(text="🔬 Аспирант")],
            [KeyboardButton(text="📝 ВКР + Статья")],
            [KeyboardButton(text="📄 Руководство по статье")],
            [KeyboardButton(text="📚 Руководство по работе")],
            [KeyboardButton(text="🔧 Другой проект")],
            [KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True
    )


def get_deadline_menu():
    """Меню выбора дедлайна"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚡ Супер срочно")],
            [KeyboardButton(text="🎓 Май")],
            [KeyboardButton(text="🗓️ Через неделю")],
            [KeyboardButton(text="📅 Указать дату")],
            [KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True
    )


def get_work_type_menu():
    """Меню выбора типа работы"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Курсовая работа")],
            [KeyboardButton(text="🎓 ВКР (Бакалавр)")],
            [KeyboardButton(text="🎓 ВКР (Магистр)")],
            [KeyboardButton(text="📄 Научная статья")],
            [KeyboardButton(text="📝 Реферат")],
            [KeyboardButton(text="🔧 Проект")],
            [KeyboardButton(text="❓ Другое")],
            [KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True
    )


def get_yes_no_menu():
    """Меню Да/Нет"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет")],
        ],
        resize_keyboard=True
    )
