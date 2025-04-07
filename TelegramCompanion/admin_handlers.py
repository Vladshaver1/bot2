import logging
import asyncio
from datetime import datetime
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import Database
from config import ADMIN_ID
from subgram_api import subgram_api

logger = logging.getLogger(__name__)
router = Router()
db = Database()

# Функция для создания кнопок админской панели
def get_admin_panel_buttons():
    """Возвращает стандартный набор кнопок для админской панели"""
    return [
        [
            InlineKeyboardButton(text="📝 Управление заданиями", callback_data="admin_manage_tasks"),
            InlineKeyboardButton(text="➕ Добавить задание", callback_data="admin_add_task")
        ],
        [
            InlineKeyboardButton(text="👥 Управление пользователями", callback_data="admin_manage_users"),
            InlineKeyboardButton(text="💰 Запросы на вывод", callback_data="admin_withdrawals")
        ],
        [
            InlineKeyboardButton(text="🔄 Обнулить звезды", callback_data="admin_reset_stars")
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings"),
            InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_mailing")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика Subgram", callback_data="admin_stats"),
            InlineKeyboardButton(text="💹 Баланс Subgram", callback_data="admin_balance")
        ]
    ]

# Admin FSM states
class AdminStates(StatesGroup):
    waiting_for_task_description = State()
    waiting_for_task_reward = State()
    waiting_for_user_search = State()
    waiting_for_stars_change = State()
    waiting_for_mailing_text = State()
    waiting_for_mailing_photo = State()
    waiting_for_mailing_button = State()
    waiting_for_min_referrals = State()
    waiting_for_min_tasks = State()
    waiting_for_partner_bonus = State()
    waiting_for_steal_percent = State()
    waiting_for_steal_unlock_tasks = State()

# Check if user is admin
def is_admin(user_id):
    return user_id == ADMIN_ID

# Admin command handler
@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.answer("У вас нет доступа к панели администратора.")
        return
    
    buttons = get_admin_panel_buttons()
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer("Панель администратора:", reply_markup=keyboard)

# Admin callback query handler
@router.callback_query(F.data.startswith("admin_"))
async def process_admin_callback(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    if not is_admin(user_id):
        await callback_query.answer("У вас нет доступа к этой функции")
        return
    
    action = callback_query.data.split("_")[1]
    
    if action == "add_task":
        await callback_query.message.edit_text("Введите описание задания:")
        await state.set_state(AdminStates.waiting_for_task_description)
    
    elif action == "manage_tasks":
        tasks = db.get_active_tasks()
        await show_tasks_management(callback_query.message, tasks)
    
    elif action == "withdrawals":
        withdrawals = db.get_pending_withdrawals()
        await show_pending_withdrawals(callback_query.message, withdrawals)
    
    elif action == "manage_users":
        await callback_query.message.edit_text(
            "Введите ID пользователя или @username для поиска:", 
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
            ])
        )
        await state.set_state(AdminStates.waiting_for_user_search)
    
    elif action == "mailing":
        await callback_query.message.edit_text(
            "Введите текст рассылки (HTML-разметка поддерживается):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_back")]
            ])
        )
        await state.set_state(AdminStates.waiting_for_mailing_text)
    
    elif action == "settings":
        settings = db.get_admin_settings()
        if settings:
            min_referrals, min_tasks, partner_bonus, steal_percent, steal_unlock_tasks = settings
            text = (
                f"<b>Текущие настройки:</b>\n\n"
                f"Минимум рефералов для вывода: {min_referrals}\n"
                f"Минимум заданий для вывода: {min_tasks}\n"
                f"Бонус за реферала: {partner_bonus} звезд\n"
                f"Процент кражи звезд: {steal_percent}%\n"
                f"Разблокировка кражи (заданий): {steal_unlock_tasks}\n"
            )
            
            buttons = [
                [InlineKeyboardButton(text="Изменить мин. рефералов", callback_data="admin_set_min_referrals")],
                [InlineKeyboardButton(text="Изменить мин. заданий", callback_data="admin_set_min_tasks")],
                [InlineKeyboardButton(text="Изменить бонус за реферала", callback_data="admin_set_partner_bonus")],
                [InlineKeyboardButton(text="Изменить процент кражи", callback_data="admin_set_steal_percent")],
                [InlineKeyboardButton(text="Изменить порог разблокировки кражи", callback_data="admin_set_steal_unlock")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            await callback_query.message.edit_text(text, reply_markup=keyboard)
            
    elif action == "stats":
        # Импортируем API для Subgram и вызываем метод получения статистики
        from subgram_api import subgram_api
        status, code, message, data, summary = await subgram_api.get_statistics(period=30)
        
        if status == "ok" and data:
            # Формируем заголовок с основной статистикой
            header = (
                f"<b>📊 Статистика Subgram за {summary['days_analyzed']} дней</b>\n\n"
                f"<b>Общая статистика:</b>\n"
                f"• Всего транзакций: {summary['total_count']}\n"
                f"• Общая сумма: {summary['total_amount']:.2f} ₽\n\n"
                f"<b>Последние 7 дней:</b>\n"
                f"• Транзакций: {summary['week_count']}\n"
                f"• Сумма: {summary['week_amount']:.2f} ₽\n\n"
                f"<b>Последний день:</b>\n"
                f"• Транзакций: {summary['day_count']}\n"
                f"• Сумма: {summary['day_amount']:.2f} ₽\n\n"
                f"<b>Средние показатели:</b>\n"
                f"• Транзакций в день: {summary['avg_count']:.2f}\n"
                f"• Сумма в день: {summary['avg_amount']:.2f} ₽\n\n"
                f"<b>Подробная статистика (последние 7 дней):</b>\n"
            )
            
            # Добавляем детализацию за последние 7 дней
            details = ""
            for i, entry in enumerate(data[:7]):
                date = entry.get("date", "Н/Д")
                count = entry.get("count", 0)
                amount = entry.get("amount", 0)
                details += f"• {date}: {count} транз., {amount:.2f} ₽\n"
            
            # Объединяем текст и добавляем кнопку возврата
            text = header + details
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
            ])
            
            await callback_query.message.edit_text(text, reply_markup=keyboard)
        else:
            # В случае ошибки выводим соответствующее сообщение
            error_text = f"<b>Ошибка получения статистики:</b>\n{message} (код: {code})"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Повторить", callback_data="admin_stats")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
            ])
            
            await callback_query.message.edit_text(error_text, reply_markup=keyboard)
    
    elif action == "balance":
        await callback_query.message.edit_text(
            "Получение баланса Subgram...",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
            ])
        )
        
        # Получаем баланс Subgram
        from subgram_api import subgram_api
        status, code, message, balance = await subgram_api.get_balance()
        
        if status == "ok":
            balance_text = (
                f"<b>💹 Баланс Subgram</b>\n\n"
                f"• Текущий баланс: <b>{balance:.2f} ₽</b>\n\n"
                f"<i>Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</i>"
            )
            
            await callback_query.message.edit_text(
                balance_text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_balance")],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
                ]),
                parse_mode="HTML"
            )
        else:
            await callback_query.message.edit_text(
                f"<b>❌ Ошибка при получении баланса Subgram</b>\n\n"
                f"Код: {code}\n"
                f"Сообщение: {message}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Повторить", callback_data="admin_balance")],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
                ]),
                parse_mode="HTML"
            )
    
    elif action == "back":
        buttons = get_admin_panel_buttons()
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback_query.message.edit_text("Панель администратора:", reply_markup=keyboard)
    
    # Settings handlers
    elif action == "set_min_referrals":
        await callback_query.message.edit_text(
            "Введите новое минимальное количество рефералов для вывода:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_settings")]
            ])
        )
        await state.set_state(AdminStates.waiting_for_min_referrals)
    
    elif action == "set_min_tasks":
        await callback_query.message.edit_text(
            "Введите новое минимальное количество заданий для вывода:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_settings")]
            ])
        )
        await state.set_state(AdminStates.waiting_for_min_tasks)
    
    elif action == "set_partner_bonus":
        await callback_query.message.edit_text(
            "Введите новый бонус за реферала (в звездах):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_settings")]
            ])
        )
        await state.set_state(AdminStates.waiting_for_partner_bonus)
    
    elif action == "set_steal_percent":
        await callback_query.message.edit_text(
            "Введите новый процент кражи звезд:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_settings")]
            ])
        )
        await state.set_state(AdminStates.waiting_for_steal_percent)
    
    elif action == "set_steal_unlock":
        await callback_query.message.edit_text(
            "Введите новое количество заданий для разблокировки кражи:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_settings")]
            ])
        )
        await state.set_state(AdminStates.waiting_for_steal_unlock_tasks)
        
    elif action == "reset_stars":
        # Запрос подтверждения перед обнулением звезд у всех пользователей
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, обнулить", callback_data="confirm_reset_stars"),
                InlineKeyboardButton(text="❌ Нет, отмена", callback_data="admin_back")
            ]
        ])
        await callback_query.message.edit_text(
            "⚠️ <b>ВНИМАНИЕ!</b> ⚠️\n\n"
            "Вы уверены, что хотите обнулить звезды у ВСЕХ пользователей?\n\n"
            "Это действие нельзя отменить!",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

# Task management
async def show_tasks_management(message, tasks):
    if tasks:
        text = "<b>Список заданий:</b>\n\n"
        buttons = []
        
        for task in tasks:
            task_id, description, reward = task
            text += f"ID: {task_id} - {description} ({reward} звезд)\n"
            buttons.append([InlineKeyboardButton(
                text=f"Переключить задание {task_id}", 
                callback_data=f"toggle_task_{task_id}"
            )])
        
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.edit_text(
            "Нет активных заданий",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
            ])
        )

# Toggle task status
@router.callback_query(F.data.startswith("toggle_task_"))
async def toggle_task(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if not is_admin(user_id):
        await callback_query.answer("У вас нет доступа к этой функции")
        return
    
    task_id = int(callback_query.data.split("_")[2])
    
    if db.toggle_task_status(task_id):
        await callback_query.answer(f"Статус задания {task_id} изменен")
        tasks = db.get_active_tasks()
        await show_tasks_management(callback_query.message, tasks)
    else:
        await callback_query.answer("Ошибка при изменении статуса задания")

# Show pending withdrawals
async def show_pending_withdrawals(message, withdrawals):
    if withdrawals:
        text = "<b>Запросы на вывод средств:</b>\n\n"
        buttons = []
        
        for withdrawal in withdrawals:
            withdrawal_id, user_id, username, amount, request_date = withdrawal
            text += (f"ID: {withdrawal_id} | Пользователь: {username or user_id} | "
                    f"Сумма: {amount} звезд | Дата: {request_date}\n\n")
            
            buttons.append([
                InlineKeyboardButton(
                    text=f"✅ Подтвердить #{withdrawal_id}", 
                    callback_data=f"approve_withdrawal_{withdrawal_id}"
                ),
                InlineKeyboardButton(
                    text=f"❌ Отклонить #{withdrawal_id}", 
                    callback_data=f"reject_withdrawal_{withdrawal_id}"
                )
            ])
        
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.edit_text(
            "Нет запросов на вывод",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
            ])
        )

# Process withdrawal
@router.callback_query(F.data.startswith(("approve_withdrawal_", "reject_withdrawal_")))
async def process_withdrawal(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if not is_admin(user_id):
        await callback_query.answer("У вас нет доступа к этой функции")
        return
    
    action, withdrawal_id = callback_query.data.split("_")[0], int(callback_query.data.split("_")[2])
    status = "approved" if action == "approve" else "rejected"
    
    if db.process_withdrawal(withdrawal_id, status):
        await callback_query.answer(f"Запрос #{withdrawal_id} {status}")
        withdrawals = db.get_pending_withdrawals()
        await show_pending_withdrawals(callback_query.message, withdrawals)
    else:
        await callback_query.answer("Ошибка при обработке запроса")

# Add task - step 1
@router.message(AdminStates.waiting_for_task_description)
async def process_task_description(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    description = message.text.strip()
    if not description:
        await message.answer("Пожалуйста, введите корректное описание задания.")
        return
    
    await state.update_data(task_description=description)
    await message.answer(
        "Введите награду за задание (количество звезд):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_back")]
        ])
    )
    await state.set_state(AdminStates.waiting_for_task_reward)

# Add task - step 2
@router.message(AdminStates.waiting_for_task_reward)
async def process_task_reward(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    try:
        reward = int(message.text.strip())
        if reward <= 0:
            raise ValueError("Reward must be positive")
        
        data = await state.get_data()
        description = data.get("task_description")
        
        task_id = db.add_task(description, reward)
        if task_id:
            await message.answer(f"✅ Задание успешно добавлено!\nID: {task_id}\nОписание: {description}\nНаграда: {reward} звезд")
        else:
            await message.answer("❌ Ошибка при добавлении задания")
        
        await state.clear()
        
        # Show admin panel
        buttons = get_admin_panel_buttons()
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await message.answer("Панель администратора:", reply_markup=keyboard)
    
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число для награды (целое положительное число).")

# User search
@router.message(AdminStates.waiting_for_user_search)
async def process_user_search(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    search_query = message.text.strip()
    
    try:
        # Try to parse as user_id
        user_id = int(search_query) if search_query.isdigit() else None
        
        # If not a user_id, check if it's a username
        if not user_id and search_query.startswith('@'):
            username = search_query[1:]  # Remove the @ symbol
            # Here we would search by username in the database
            # For now, just show an error
            await message.answer(
                f"Поиск пользователя по имени пользователя не реализован. Используйте ID пользователя.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
                ])
            )
            return
        
        if not user_id:
            await message.answer(
                "Пожалуйста, введите корректный ID пользователя или @username",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
                ])
            )
            return
        
        # Get user from database
        user = db.get_user(user_id)
        
        if not user:
            await message.answer(
                f"Пользователь с ID {user_id} не найден",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
                ])
            )
            return
        
        # Display user info
        user_id, username, full_name, referral_id, stars, completed_tasks, referrals_count, last_activity, is_banned, reg_date = user[:10]
        
        ban_status = "Забанен" if is_banned else "Активен"
        
        user_info = (
            f"<b>Информация о пользователе:</b>\n\n"
            f"ID: {user_id}\n"
            f"Имя пользователя: {username or 'Не указано'}\n"
            f"Полное имя: {full_name}\n"
            f"Статус: {ban_status}\n"
            f"Звезды: {stars}\n"
            f"Выполнено заданий: {completed_tasks}\n"
            f"Рефералов: {referrals_count}\n"
            f"Пришел по рефералу: {referral_id or 'Нет'}\n"
            f"Последняя активность: {last_activity}\n"
            f"Дата регистрации: {reg_date}\n"
        )
        
        buttons = [
            [
                InlineKeyboardButton(text="Изменить звезды", callback_data=f"edit_stars_{user_id}"),
                InlineKeyboardButton(
                    text="Разбанить" if is_banned else "Забанить", 
                    callback_data=f"toggle_ban_{user_id}"
                )
            ],
            [InlineKeyboardButton(text="❌ Удалить пользователя", callback_data=f"delete_user_{user_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await message.answer(user_info, reply_markup=keyboard)
        await state.clear()
    
    except Exception as e:
        logger.error(f"Error in process_user_search: {e}")
        await message.answer(
            "Произошла ошибка при поиске пользователя",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
            ])
        )

# Edit user stars
@router.callback_query(F.data.startswith("edit_stars_"))
async def edit_stars(callback_query: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("У вас нет доступа к этой функции")
        return
    
    user_id = int(callback_query.data.split("_")[2])
    
    await state.update_data(edit_user_id=user_id)
    await callback_query.message.edit_text(
        f"Введите изменение количества звезд для пользователя {user_id}.\n"
        f"Используйте '+' или '-' перед числом, например: +10 или -5",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_back")]
        ])
    )
    await state.set_state(AdminStates.waiting_for_stars_change)

# Process stars change
@router.message(AdminStates.waiting_for_stars_change)
async def process_stars_change(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    try:
        stars_change = message.text.strip()
        if not (stars_change.startswith('+') or stars_change.startswith('-')):
            await message.answer("Пожалуйста, используйте '+' или '-' перед числом")
            return
        
        stars_change = int(stars_change)
        
        data = await state.get_data()
        user_id = data.get("edit_user_id")
        
        if db.update_user_stars(user_id, stars_change):
            await message.answer(f"✅ Звезды пользователя {user_id} изменены на {stars_change}")
        else:
            await message.answer(f"❌ Ошибка при изменении звезд пользователя {user_id}")
        
        await state.clear()
        
        # Show admin panel
        buttons = get_admin_panel_buttons()
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await message.answer("Панель администратора:", reply_markup=keyboard)
    
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число")

# Toggle user ban status
@router.callback_query(F.data.startswith("toggle_ban_"))
async def toggle_ban(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split("_")[2])
    
    # Get current ban status
    user = db.get_user(user_id)
    if not user:
        await callback_query.answer("Пользователь не найден")
        return
    
    is_banned = user[8]
    new_status = 0 if is_banned else 1
    
    if db.ban_user(user_id, new_status):
        status_text = "забанен" if new_status else "разбанен"
        await callback_query.answer(f"Пользователь {user_id} {status_text}")
        
        # Update message with new ban status
        user = db.get_user(user_id)
        user_id, username, full_name, referral_id, stars, completed_tasks, referrals_count, last_activity, is_banned, reg_date = user[:10]
        
        ban_status = "Забанен" if is_banned else "Активен"
        
        user_info = (
            f"<b>Информация о пользователе:</b>\n\n"
            f"ID: {user_id}\n"
            f"Имя пользователя: {username or 'Не указано'}\n"
            f"Полное имя: {full_name}\n"
            f"Статус: {ban_status}\n"
            f"Звезды: {stars}\n"
            f"Выполнено заданий: {completed_tasks}\n"
            f"Рефералов: {referrals_count}\n"
            f"Пришел по рефералу: {referral_id or 'Нет'}\n"
            f"Последняя активность: {last_activity}\n"
            f"Дата регистрации: {reg_date}\n"
        )
        
        buttons = [
            [
                InlineKeyboardButton(text="Изменить звезды", callback_data=f"edit_stars_{user_id}"),
                InlineKeyboardButton(
                    text="Разбанить" if is_banned else "Забанить", 
                    callback_data=f"toggle_ban_{user_id}"
                )
            ],
            [InlineKeyboardButton(text="❌ Удалить пользователя", callback_data=f"delete_user_{user_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback_query.message.edit_text(user_info, reply_markup=keyboard)
    else:
        await callback_query.answer("Ошибка при изменении статуса пользователя")

# Handle user deletion
@router.callback_query(F.data.startswith("delete_user_"))
async def delete_user(callback_query: types.CallbackQuery):
    """Полностью удаляет пользователя из базы данных"""
    user_id = int(callback_query.data.split("_")[2])
    
    # Запрос подтверждения перед удалением
    buttons = [
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{user_id}"),
            InlineKeyboardButton(text="❌ Нет, отмена", callback_data=f"cancel_delete_{user_id}")
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback_query.message.edit_text(
        f"⚠️ <b>ВНИМАНИЕ!</b> ⚠️\n\n"
        f"Вы собираетесь полностью удалить пользователя с ID {user_id}.\n"
        f"Это действие нельзя отменить!\n\n"
        f"Все данные пользователя будут удалены из базы данных, включая:\n"
        f"- Информацию профиля\n"
        f"- Историю заданий\n"
        f"- Историю выводов\n"
        f"- Игровую статистику\n"
        f"- Историю подписок\n"
        f"- Историю обменов\n\n"
        f"Уверены, что хотите продолжить?",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

# Confirm user deletion
@router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete_user(callback_query: types.CallbackQuery):
    """Подтверждение удаления пользователя"""
    user_id = int(callback_query.data.split("_")[2])
    
    # Удаляем пользователя
    if db.delete_user(user_id):
        await callback_query.answer(f"Пользователь {user_id} успешно удален")
        await callback_query.message.edit_text(
            f"✅ Пользователь с ID {user_id} успешно удален из базы данных.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
            ])
        )
    else:
        await callback_query.answer("Ошибка при удалении пользователя")
        await callback_query.message.edit_text(
            f"❌ Произошла ошибка при удалении пользователя с ID {user_id}.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Повторить", callback_data=f"delete_user_{user_id}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
            ])
        )

# Cancel user deletion
@router.callback_query(F.data.startswith("cancel_delete_"))
async def cancel_delete_user(callback_query: types.CallbackQuery):
    """Отмена удаления пользователя"""
    user_id = int(callback_query.data.split("_")[2])
    
    # Получаем информацию о пользователе для возврата к экрану информации
    user = db.get_user(user_id)
    if not user:
        await callback_query.answer("Пользователь не найден")
        # Возвращаемся в админ-панель
        buttons = get_admin_panel_buttons()
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback_query.message.edit_text("Панель администратора:", reply_markup=keyboard)
        return
    
    user_id, username, full_name, referral_id, stars, completed_tasks, referrals_count, last_activity, is_banned, reg_date = user[:10]
    
    ban_status = "Забанен" if is_banned else "Активен"
    
    user_info = (
        f"<b>Информация о пользователе:</b>\n\n"
        f"ID: {user_id}\n"
        f"Имя пользователя: {username or 'Не указано'}\n"
        f"Полное имя: {full_name}\n"
        f"Статус: {ban_status}\n"
        f"Звезды: {stars}\n"
        f"Выполнено заданий: {completed_tasks}\n"
        f"Рефералов: {referrals_count}\n"
        f"Пришел по рефералу: {referral_id or 'Нет'}\n"
        f"Последняя активность: {last_activity}\n"
        f"Дата регистрации: {reg_date}\n"
    )
    
    buttons = [
        [
            InlineKeyboardButton(text="Изменить звезды", callback_data=f"edit_stars_{user_id}"),
            InlineKeyboardButton(
                text="Разбанить" if is_banned else "Забанить", 
                callback_data=f"toggle_ban_{user_id}"
            )
        ],
        [InlineKeyboardButton(text="❌ Удалить пользователя", callback_data=f"delete_user_{user_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback_query.message.edit_text(user_info, reply_markup=keyboard)

# Mailing step 1 - get text
@router.message(AdminStates.waiting_for_mailing_text)
async def process_mailing_text(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    mailing_text = message.text.strip()
    if not mailing_text:
        await message.answer("Пожалуйста, введите текст рассылки.")
        return
    
    await state.update_data(mailing_text=mailing_text)
    
    # Ask if admin wants to add a photo
    buttons = [
        [
            InlineKeyboardButton(text="Добавить фото", callback_data="mailing_add_photo"),
            InlineKeyboardButton(text="Без фото", callback_data="mailing_no_photo")
        ],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_back")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer("Хотите добавить фото к рассылке?", reply_markup=keyboard)

# Mailing - add photo decision
@router.callback_query(F.data.startswith("mailing_"))
async def mailing_photo_decision(callback_query: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("У вас нет доступа к этой функции")
        return
    
    action = callback_query.data.split("_")[1]
    
    if action == "add_photo":
        await callback_query.message.edit_text(
            "Отправьте фото для рассылки:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_back")]
            ])
        )
        await state.set_state(AdminStates.waiting_for_mailing_photo)
    
    elif action == "no_photo":
        # Ask if admin wants to add a button
        buttons = [
            [
                InlineKeyboardButton(text="Добавить кнопку", callback_data="mailing_add_button"),
                InlineKeyboardButton(text="Без кнопки", callback_data="mailing_no_button")
            ],
            [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_back")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback_query.message.edit_text("Хотите добавить кнопку к рассылке?", reply_markup=keyboard)
    
    elif action == "add_button":
        await callback_query.message.edit_text(
            "Введите текст кнопки и URL через пробел, например: 'Наш канал https://t.me/channel'",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_back")]
            ])
        )
        await state.set_state(AdminStates.waiting_for_mailing_button)
    
    elif action == "no_button":
        # Start the mailing
        data = await state.get_data()
        mailing_text = data.get("mailing_text")
        
        await callback_query.message.edit_text("Начинаем рассылку...")
        
        # Get all users
        await start_mailing(callback_query.message, mailing_text)
        await state.clear()

# Mailing - get photo
@router.message(AdminStates.waiting_for_mailing_photo)
async def process_mailing_photo(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not message.photo:
        await message.answer("Пожалуйста, отправьте фото для рассылки.")
        return
    
    photo_id = message.photo[-1].file_id
    await state.update_data(mailing_photo=photo_id)
    
    # Ask if admin wants to add a button
    buttons = [
        [
            InlineKeyboardButton(text="Добавить кнопку", callback_data="mailing_add_button"),
            InlineKeyboardButton(text="Без кнопки", callback_data="mailing_no_button")
        ],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_back")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer("Хотите добавить кнопку к рассылке?", reply_markup=keyboard)

# Mailing - get button
@router.message(AdminStates.waiting_for_mailing_button)
async def process_mailing_button(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    try:
        button_text_url = message.text.strip()
        if ' ' not in button_text_url:
            await message.answer("Пожалуйста, введите текст кнопки и URL через пробел.")
            return
        
        button_text, button_url = button_text_url.split(' ', 1)
        
        if not button_text or not button_url:
            await message.answer("Пожалуйста, укажите корректный текст кнопки и URL.")
            return
        
        await state.update_data(mailing_button_text=button_text, mailing_button_url=button_url)
        
        data = await state.get_data()
        mailing_text = data.get("mailing_text")
        mailing_photo = data.get("mailing_photo")
        
        # Preview the mailing
        if mailing_photo:
            buttons = [
                [InlineKeyboardButton(text=button_text, url=button_url)]
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            await message.answer_photo(
                photo=mailing_photo,
                caption=mailing_text,
                reply_markup=keyboard
            )
        else:
            buttons = [
                [InlineKeyboardButton(text=button_text, url=button_url)]
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            await message.answer(mailing_text, reply_markup=keyboard)
        
        # Confirm mailing
        confirm_buttons = [
            [
                InlineKeyboardButton(text="✅ Начать рассылку", callback_data="confirm_mailing"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="admin_back")
            ]
        ]
        confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=confirm_buttons)
        
        await message.answer("Подтвердите рассылку:", reply_markup=confirm_keyboard)
    
    except Exception as e:
        logger.error(f"Error in process_mailing_button: {e}")
        await message.answer("Произошла ошибка при обработке кнопки для рассылки")

# Confirm and start mailing
# Обработчик подтверждения обнуления звезд
@router.callback_query(F.data == "confirm_reset_stars")
async def confirm_reset_stars(callback_query: types.CallbackQuery):
    """Обнуление звезд у всех пользователей"""
    user_id = callback_query.from_user.id
    if not is_admin(user_id):
        await callback_query.answer("У вас нет доступа к этой функции")
        return
    
    # Обнуляем звезды у всех пользователей
    success, message = db.reset_all_users_stars()
    
    if success:
        await callback_query.answer("Звезды всех пользователей обнулены")
        await callback_query.message.edit_text(
            "✅ Операция выполнена успешно!\n\n" + message,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
            ])
        )
    else:
        await callback_query.answer("Ошибка при обнулении звезд")
        await callback_query.message.edit_text(
            "❌ Произошла ошибка:\n\n" + message,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Повторить", callback_data="admin_reset_stars")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
            ])
        )

@router.callback_query(F.data == "confirm_mailing")
async def confirm_mailing(callback_query: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("У вас нет доступа к этой функции")
        return
    
    data = await state.get_data()
    mailing_text = data.get("mailing_text")
    mailing_photo = data.get("mailing_photo")
    mailing_button_text = data.get("mailing_button_text")
    mailing_button_url = data.get("mailing_button_url")
    
    await callback_query.message.edit_text("Начинаем рассылку...")
    
    # Start mailing
    if mailing_button_text and mailing_button_url:
        buttons = [
            [InlineKeyboardButton(text=mailing_button_text, url=mailing_button_url)]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    else:
        keyboard = None
    
    await start_mailing(callback_query.message, mailing_text, mailing_photo, keyboard)
    await state.clear()

# Start mailing to all users
async def start_mailing(message, text, photo_id=None, keyboard=None):
    try:
        # Get all users
        cursor = db.conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE is_banned = 0')
        users = cursor.fetchall()
        
        sent = 0
        failed = 0
        
        for user in users:
            user_id = user[0]
            try:
                if photo_id:
                    await message.bot.send_photo(user_id, photo=photo_id, caption=text, reply_markup=keyboard)
                else:
                    await message.bot.send_message(user_id, text, reply_markup=keyboard)
                sent += 1
                # Add delay to avoid flooding
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
                failed += 1
        
        await message.edit_text(
            f"Рассылка завершена!\n✅ Отправлено: {sent}\n❌ Не отправлено: {failed}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
            ])
        )
    
    except Exception as e:
        logger.error(f"Error in start_mailing: {e}")
        await message.edit_text(
            f"Ошибка при выполнении рассылки: {e}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
            ])
        )

# Admin settings handlers
@router.message(AdminStates.waiting_for_min_referrals)
async def process_min_referrals(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    try:
        min_referrals = int(message.text.strip())
        if min_referrals < 0:
            raise ValueError("Min referrals must be non-negative")
        
        if db.update_admin_settings(min_referrals=min_referrals):
            await message.answer(f"✅ Минимальное количество рефералов изменено на {min_referrals}")
        else:
            await message.answer("❌ Ошибка при изменении настроек")
        
        await state.clear()
        
        # Show updated settings
        settings = db.get_admin_settings()
        if settings:
            min_referrals, min_tasks, partner_bonus, steal_percent, steal_unlock_tasks = settings
            text = (
                f"<b>Текущие настройки:</b>\n\n"
                f"Минимум рефералов для вывода: {min_referrals}\n"
                f"Минимум заданий для вывода: {min_tasks}\n"
                f"Бонус за реферала: {partner_bonus} звезд\n"
                f"Процент кражи звезд: {steal_percent}%\n"
                f"Разблокировка кражи (заданий): {steal_unlock_tasks}\n"
            )
            
            buttons = [
                [InlineKeyboardButton(text="Изменить мин. рефералов", callback_data="admin_set_min_referrals")],
                [InlineKeyboardButton(text="Изменить мин. заданий", callback_data="admin_set_min_tasks")],
                [InlineKeyboardButton(text="Изменить бонус за реферала", callback_data="admin_set_partner_bonus")],
                [InlineKeyboardButton(text="Изменить процент кражи", callback_data="admin_set_steal_percent")],
                [InlineKeyboardButton(text="Изменить порог разблокировки кражи", callback_data="admin_set_steal_unlock")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            await message.answer(text, reply_markup=keyboard)
    
    except ValueError:
        await message.answer("Пожалуйста, введите корректное положительное число")

@router.message(AdminStates.waiting_for_min_tasks)
async def process_min_tasks(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    try:
        min_tasks = int(message.text.strip())
        if min_tasks < 0:
            raise ValueError("Min tasks must be non-negative")
        
        if db.update_admin_settings(min_tasks=min_tasks):
            await message.answer(f"✅ Минимальное количество заданий изменено на {min_tasks}")
        else:
            await message.answer("❌ Ошибка при изменении настроек")
        
        await state.clear()
        
        # Show updated settings
        settings = db.get_admin_settings()
        if settings:
            min_referrals, min_tasks, partner_bonus, steal_percent, steal_unlock_tasks = settings
            text = (
                f"<b>Текущие настройки:</b>\n\n"
                f"Минимум рефералов для вывода: {min_referrals}\n"
                f"Минимум заданий для вывода: {min_tasks}\n"
                f"Бонус за реферала: {partner_bonus} звезд\n"
                f"Процент кражи звезд: {steal_percent}%\n"
                f"Разблокировка кражи (заданий): {steal_unlock_tasks}\n"
            )
            
            buttons = [
                [InlineKeyboardButton(text="Изменить мин. рефералов", callback_data="admin_set_min_referrals")],
                [InlineKeyboardButton(text="Изменить мин. заданий", callback_data="admin_set_min_tasks")],
                [InlineKeyboardButton(text="Изменить бонус за реферала", callback_data="admin_set_partner_bonus")],
                [InlineKeyboardButton(text="Изменить процент кражи", callback_data="admin_set_steal_percent")],
                [InlineKeyboardButton(text="Изменить порог разблокировки кражи", callback_data="admin_set_steal_unlock")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            await message.answer(text, reply_markup=keyboard)
    
    except ValueError:
        await message.answer("Пожалуйста, введите корректное положительное число")

@router.message(AdminStates.waiting_for_partner_bonus)
async def process_partner_bonus(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    try:
        partner_bonus = int(message.text.strip())
        if partner_bonus < 0:
            raise ValueError("Partner bonus must be non-negative")
        
        if db.update_admin_settings(partner_bonus=partner_bonus):
            await message.answer(f"✅ Бонус за реферала изменен на {partner_bonus}")
        else:
            await message.answer("❌ Ошибка при изменении настроек")
        
        await state.clear()
        
        # Show updated settings
        settings = db.get_admin_settings()
        if settings:
            min_referrals, min_tasks, partner_bonus, steal_percent, steal_unlock_tasks = settings
            text = (
                f"<b>Текущие настройки:</b>\n\n"
                f"Минимум рефералов для вывода: {min_referrals}\n"
                f"Минимум заданий для вывода: {min_tasks}\n"
                f"Бонус за реферала: {partner_bonus} звезд\n"
                f"Процент кражи звезд: {steal_percent}%\n"
                f"Разблокировка кражи (заданий): {steal_unlock_tasks}\n"
            )
            
            buttons = [
                [InlineKeyboardButton(text="Изменить мин. рефералов", callback_data="admin_set_min_referrals")],
                [InlineKeyboardButton(text="Изменить мин. заданий", callback_data="admin_set_min_tasks")],
                [InlineKeyboardButton(text="Изменить бонус за реферала", callback_data="admin_set_partner_bonus")],
                [InlineKeyboardButton(text="Изменить процент кражи", callback_data="admin_set_steal_percent")],
                [InlineKeyboardButton(text="Изменить порог разблокировки кражи", callback_data="admin_set_steal_unlock")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            await message.answer(text, reply_markup=keyboard)
    
    except ValueError:
        await message.answer("Пожалуйста, введите корректное положительное число")

@router.message(AdminStates.waiting_for_steal_percent)
async def process_steal_percent(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    try:
        steal_percent = int(message.text.strip())
        if steal_percent < 0 or steal_percent > 100:
            raise ValueError("Steal percent must be between 0 and 100")
        
        if db.update_admin_settings(steal_percent=steal_percent):
            await message.answer(f"✅ Процент кражи изменен на {steal_percent}%")
        else:
            await message.answer("❌ Ошибка при изменении настроек")
        
        await state.clear()
        
        # Show updated settings
        settings = db.get_admin_settings()
        if settings:
            min_referrals, min_tasks, partner_bonus, steal_percent, steal_unlock_tasks = settings
            text = (
                f"<b>Текущие настройки:</b>\n\n"
                f"Минимум рефералов для вывода: {min_referrals}\n"
                f"Минимум заданий для вывода: {min_tasks}\n"
                f"Бонус за реферала: {partner_bonus} звезд\n"
                f"Процент кражи звезд: {steal_percent}%\n"
                f"Разблокировка кражи (заданий): {steal_unlock_tasks}\n"
            )
            
            buttons = [
                [InlineKeyboardButton(text="Изменить мин. рефералов", callback_data="admin_set_min_referrals")],
                [InlineKeyboardButton(text="Изменить мин. заданий", callback_data="admin_set_min_tasks")],
                [InlineKeyboardButton(text="Изменить бонус за реферала", callback_data="admin_set_partner_bonus")],
                [InlineKeyboardButton(text="Изменить процент кражи", callback_data="admin_set_steal_percent")],
                [InlineKeyboardButton(text="Изменить порог разблокировки кражи", callback_data="admin_set_steal_unlock")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            await message.answer(text, reply_markup=keyboard)
    
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число от 0 до 100")

@router.message(AdminStates.waiting_for_steal_unlock_tasks)
async def process_steal_unlock_tasks(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    try:
        steal_unlock_tasks = int(message.text.strip())
        if steal_unlock_tasks < 0:
            raise ValueError("Steal unlock tasks must be non-negative")
        
        if db.update_admin_settings(steal_unlock_tasks=steal_unlock_tasks):
            await message.answer(f"✅ Порог разблокировки кражи изменен на {steal_unlock_tasks} заданий")
        else:
            await message.answer("❌ Ошибка при изменении настроек")
        
        await state.clear()
        
        # Show updated settings
        settings = db.get_admin_settings()
        if settings:
            min_referrals, min_tasks, partner_bonus, steal_percent, steal_unlock_tasks = settings
            text = (
                f"<b>Текущие настройки:</b>\n\n"
                f"Минимум рефералов для вывода: {min_referrals}\n"
                f"Минимум заданий для вывода: {min_tasks}\n"
                f"Бонус за реферала: {partner_bonus} звезд\n"
                f"Процент кражи звезд: {steal_percent}%\n"
                f"Разблокировка кражи (заданий): {steal_unlock_tasks}\n"
            )
            
            buttons = [
                [InlineKeyboardButton(text="Изменить мин. рефералов", callback_data="admin_set_min_referrals")],
                [InlineKeyboardButton(text="Изменить мин. заданий", callback_data="admin_set_min_tasks")],
                [InlineKeyboardButton(text="Изменить бонус за реферала", callback_data="admin_set_partner_bonus")],
                [InlineKeyboardButton(text="Изменить процент кражи", callback_data="admin_set_steal_percent")],
                [InlineKeyboardButton(text="Изменить порог разблокировки кражи", callback_data="admin_set_steal_unlock")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            await message.answer(text, reply_markup=keyboard)
    
    except ValueError:
        await message.answer("Пожалуйста, введите корректное положительное число")
