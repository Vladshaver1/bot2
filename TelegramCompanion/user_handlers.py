import logging
import random
from aiogram import types, Bot, F, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import (
    register_user, get_user_stats, get_admin_settings, get_tasks,
    complete_task, get_top_users, update_user_stars
)
from keyboards import (
    get_main_menu_keyboard, get_back_button, get_tasks_keyboard
)
from utils import escape_html

logger = logging.getLogger(__name__)

# Register handlers
def register_handlers(dp: Dispatcher, bot: Bot):
    # Basic commands
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
    
    # Menu navigation
    dp.callback_query.register(show_main_menu, F.data == "main_menu")
    dp.callback_query.register(show_balance, F.data == "my_balance")
    dp.callback_query.register(show_tasks, F.data == "tasks_list")
    dp.callback_query.register(show_top_players, F.data == "top_players")
    
    # Task completion
    dp.callback_query.register(complete_task_handler, F.data.startswith("complete_task_"))
    
    # Steal stars feature
    dp.callback_query.register(steal_stars, F.data.startswith("steal_stars_"))
    
    logger.info("User handlers registered")

# Command handlers
async def cmd_start(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        username = message.from_user.username
        full_name = message.from_user.full_name
        referral_id = None
        
        # Check for referral
        if len(message.text.split()) > 1:
            try:
                referral_id = int(message.text.split()[1])
                # Don't allow self-referrals
                if referral_id == user_id:
                    referral_id = None
            except ValueError:
                pass
        
        # Register user
        is_new = register_user(user_id, username, full_name, referral_id)
        
        if is_new:
            # Welcome message for new users
            welcome_text = (
                "👋 <b>Добро пожаловать в бота!</b>\n\n"
                "💎 Здесь вы можете зарабатывать звезды, выполняя задания и приглашая друзей.\n\n"
                "🔹 Выполняйте задания и получайте звезды\n"
                "🔹 Приглашайте друзей и получайте бонусы\n"
                "🔹 Участвуйте в мини-играх\n"
                "🔹 Выводите заработанные звезды\n\n"
                "📌 Используйте кнопки меню для навигации"
            )
            
            bot_info = await bot.get_me()
            keyboard = get_main_menu_keyboard(user_id, bot_info.username)
            
            await message.answer(welcome_text, reply_markup=keyboard)
        else:
            # Returning user message
            await show_main_menu_message(message, bot)
            
    except Exception as e:
        logger.error(f"Error in cmd_start: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

async def cmd_help(message: types.Message):
    help_text = (
        "📚 <b>Справка по боту</b>\n\n"
        "Этот бот позволяет вам зарабатывать звезды, выполняя задания и приглашая друзей.\n\n"
        "<b>Основные команды:</b>\n"
        "/start - Запустить бота\n"
        "/help - Показать справку\n\n"
        "<b>Как заработать звезды:</b>\n"
        "- Выполняйте задания в разделе «Список заданий»\n"
        "- Приглашайте друзей, получайте бонус за каждого\n"
        "- Играйте в мини-игры и выигрывайте звезды\n\n"
        "<b>Вывод звезд:</b>\n"
        "Для вывода вам необходимо выполнить условия:\n"
        "1. Пригласить определенное количество друзей\n"
        "2. Выполнить определенное количество заданий\n\n"
        "После этого вы сможете обменять звезды на реальные призы или деньги!"
    )
    
    bot_info = await message.bot.get_me()
    keyboard = get_main_menu_keyboard(message.from_user.id, bot_info.username)
    
    await message.answer(help_text, reply_markup=keyboard)

# Menu navigation
async def show_main_menu(callback: types.CallbackQuery):
    await show_main_menu_message(callback.message, callback.bot, is_edit=True)
    await callback.answer()

async def show_main_menu_message(message: types.Message, bot: Bot, is_edit=False):
    bot_info = await bot.get_me()
    keyboard = get_main_menu_keyboard(message.chat.id, bot_info.username)
    
    menu_text = (
        "🌟 <b>Главное меню</b>\n\n"
        "Добро пожаловать в меню управления!\n"
        "Выберите нужный раздел:"
    )
    
    if is_edit:
        await message.edit_text(menu_text, reply_markup=keyboard)
    else:
        await message.answer(menu_text, reply_markup=keyboard)

async def show_balance(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id
        
        user_stats = get_user_stats(user_id)
        
        if user_stats:
            stars, completed_tasks, referrals_count = user_stats
            
            settings = get_admin_settings()
            if settings:
                min_referrals, min_tasks, partner_bonus, steal_percent, steal_unlock_tasks = settings
                
                balance_text = (
                    f"💎 <b>Ваш баланс</b>: {stars} звезд\n\n"
                    f"📊 <b>Статистика:</b>\n"
                    f"✅ Выполнено заданий: {completed_tasks}/{min_tasks}\n"
                    f"👥 Приглашено друзей: {referrals_count}/{min_referrals}\n\n"
                )
                
                if completed_tasks >= min_tasks and referrals_count >= min_referrals:
                    balance_text += "🎉 <b>Вы выполнили все условия для вывода звезд!</b>"
                    
                    buttons = [
                        [InlineKeyboardButton(text="💸 Вывести звезды", callback_data="withdraw")],
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
                    ]
                    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
                else:
                    balance_text += (
                        f"⚠️ <b>Для вывода необходимо:</b>\n"
                        f"- Пригласить {min_referrals} друзей (осталось {max(0, min_referrals - referrals_count)})\n"
                        f"- Выполнить {min_tasks} заданий (осталось {max(0, min_tasks - completed_tasks)})\n"
                    )
                    
                    # Add steal feature if eligible
                    if completed_tasks >= steal_unlock_tasks:
                        balance_text += f"\n🔓 <b>Доступна кража звезд!</b>\nВы можете украсть {steal_percent}% звезд у случайного пользователя."
                        
                        buttons = [
                            [InlineKeyboardButton(text="🔍 Украсть звезды", callback_data="steal_stars_random")],
                            [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
                        ]
                        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
                    else:
                        balance_text += f"\n🔒 <b>Кража звезд заблокирована</b>\nВыполните еще {max(0, steal_unlock_tasks - completed_tasks)} заданий, чтобы разблокировать."
                        keyboard = get_back_button()
            else:
                balance_text = "💎 <b>Ваш баланс</b>: {stars} звезд\n\nОшибка при загрузке дополнительной информации."
                keyboard = get_back_button()
        else:
            balance_text = "❌ Произошла ошибка при получении данных о балансе."
            keyboard = get_back_button()
        
        await callback.message.edit_text(balance_text, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in show_balance: {e}")
        await callback.answer("Произошла ошибка при отображении баланса")

async def show_tasks(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id
        
        user_tasks = get_tasks(user_id)
        
        if user_tasks:
            tasks_text = "📝 <b>Список доступных заданий</b>\n\n"
            
            for task_id, description, reward, completed in user_tasks:
                status = "✅ Выполнено" if completed else "❌ Не выполнено"
                tasks_text += f"{task_id}. {escape_html(description)}\n💰 Награда: {reward} звезд ({status})\n\n"
            
            keyboard = get_tasks_keyboard(user_tasks, user_id)
        else:
            tasks_text = "📝 <b>Список заданий</b>\n\nНет доступных заданий."
            keyboard = get_back_button()
        
        await callback.message.edit_text(tasks_text, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in show_tasks: {e}")
        await callback.answer("Произошла ошибка при отображении заданий")

async def show_top_players(callback: types.CallbackQuery):
    try:
        top_users = get_top_users(10)
        
        if top_users:
            top_text = "🏆 <b>Топ 10 игроков</b>\n\n"
            
            for i, (user_id, username, full_name, stars, referrals) in enumerate(top_users, 1):
                user_name = username if username else full_name
                if i == 1:
                    top_text += f"🥇 {i}. {escape_html(user_name)} - {stars} звезд, {referrals} рефералов\n"
                elif i == 2:
                    top_text += f"🥈 {i}. {escape_html(user_name)} - {stars} звезд, {referrals} рефералов\n"
                elif i == 3:
                    top_text += f"🥉 {i}. {escape_html(user_name)} - {stars} звезд, {referrals} рефералов\n"
                else:
                    top_text += f"🔸 {i}. {escape_html(user_name)} - {stars} звезд, {referrals} рефералов\n"
        else:
            top_text = "🏆 <b>Топ игроков</b>\n\nПока нет данных о пользователях."
        
        await callback.message.edit_text(top_text, reply_markup=get_back_button())
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in show_top_players: {e}")
        await callback.answer("Произошла ошибка при отображении топа игроков")

# Task completion
async def complete_task_handler(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id
        task_id = int(callback.data.split("_")[2])
        
        success, message_text = complete_task(user_id, task_id)
        
        await callback.answer(message_text, show_alert=True)
        
        # Refresh tasks list
        await show_tasks(callback)
    except Exception as e:
        logger.error(f"Error in complete_task_handler: {e}")
        await callback.answer("Произошла ошибка при выполнении задания")

# Steal stars feature
async def steal_stars(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id
        
        # Get user stats
        user_stats = get_user_stats(user_id)
        if not user_stats:
            await callback.answer("❌ Произошла ошибка при получении данных.", show_alert=True)
            return
        
        # Get admin settings
        settings = get_admin_settings()
        if not settings:
            await callback.answer("❌ Произошла ошибка при получении настроек.", show_alert=True)
            return
        
        completed_tasks = user_stats[1]
        min_referrals, min_tasks, partner_bonus, steal_percent, steal_unlock_tasks = settings
        
        # Check if the user can steal
        if completed_tasks < steal_unlock_tasks:
            await callback.answer(
                f"🔒 Кража звезд заблокирована. Выполните еще {steal_unlock_tasks - completed_tasks} заданий.",
                show_alert=True
            )
            return
        
        # Get top users to steal from (except the current user)
        top_users = get_top_users(50)
        if not top_users:
            await callback.answer("❌ Нет пользователей для кражи звезд.", show_alert=True)
            return
        
        # Filter out current user and users with no stars
        potential_victims = [(uid, stars) for uid, _, _, stars, _ in top_users 
                            if uid != user_id and stars > 0]
        
        if not potential_victims:
            await callback.answer("❌ Нет пользователей для кражи звезд.", show_alert=True)
            return
        
        # Randomly select a victim
        victim_id, victim_stars = random.choice(potential_victims)
        
        # Calculate stars to steal
        stars_to_steal = max(1, int(victim_stars * (steal_percent / 100)))
        
        # Update user balances
        if update_user_stars(victim_id, -stars_to_steal) and update_user_stars(user_id, stars_to_steal):
            await callback.answer(
                f"🔍 Вы украли {stars_to_steal} звезд у пользователя с ID {victim_id}!",
                show_alert=True
            )
            
            # Refresh balance
            await show_balance(callback)
        else:
            await callback.answer("❌ Произошла ошибка при краже звезд.", show_alert=True)
    except Exception as e:
        logger.error(f"Error in steal_stars: {e}")
        await callback.answer("Произошла ошибка при краже звезд")
