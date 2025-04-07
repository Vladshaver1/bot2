import logging
import random
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import datetime

from database import Database
from mini_games import Games
from config import GAME_DAILY_LIMIT

logger = logging.getLogger(__name__)
router = Router()
db = Database()
games = Games(db)

# FSM states
class WithdrawStates(StatesGroup):
    waiting_for_withdraw_amount = State()

# Main menu handler
@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback_query: types.CallbackQuery):
    try:
        user_id = callback_query.from_user.id

        # Update user activity
        db.update_user_activity(user_id)

        buttons = [
            [InlineKeyboardButton(
                text="📢 Поделиться ссылкой", 
                switch_inline_query=f"Присоединяйся к боту и зарабатывай звезды! https://t.me/{(await callback_query.bot.get_me()).username}?start={user_id}"
            )],
            [
                InlineKeyboardButton(text="📝 Список заданий", callback_data="tasks_list"),
                InlineKeyboardButton(text="💰 Мой баланс", callback_data="my_balance")
            ],
            [
                InlineKeyboardButton(text="🎮 Мини-игры", callback_data="mini_games"),
                InlineKeyboardButton(text="🏆 Топ игроков", callback_data="top_players")
            ],
            [InlineKeyboardButton(text="💸 Вывод звезд", callback_data="withdraw"), InlineKeyboardButton(text="❓ FAQ", callback_data="show_faq")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback_query.message.edit_text("Главное меню:", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in show_main_menu: {e}")
        await callback_query.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

# Start command handler
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username
        full_name = message.from_user.full_name
        referral_id = None

        # Check if the message contains a referral code
        if len(message.text.split()) > 1:
            try:
                referral_id = int(message.text.split()[1])
            except ValueError:
                pass

        # Check if user already exists
        user = db.get_user(user_id)

        if not user:
            # Register new user
            db.add_user(user_id, username, full_name, referral_id)

            # Add referral bonus if needed
            if referral_id:
                db.increase_referral_count(referral_id)

            welcome_text = (
                "👋 Добро пожаловать в бота!\n\n"
                "💎 Здесь вы можете зарабатывать звезды, выполняя задания и приглашая друзей.\n\n"
                "🔹 Выполняйте задания и получайте звезды\n"
                "🔹 Приглашайте друзей и получайте бонусы\n"
                "🔹 Участвуйте в мини-играх\n"
                "🔹 Выводите заработанные звезды\n\n"
                "📌 Используйте кнопки меню для навигации"
            )

            buttons = [
                [InlineKeyboardButton(
                    text="📢 Поделиться ссылкой", 
                    switch_inline_query=f"Присоединяйся к боту и зарабатывай звезды! https://t.me/{(await message.bot.get_me()).username}?start={user_id}"
                )],
                [
                    InlineKeyboardButton(text="📝 Список заданий", callback_data="tasks_list"),
                    InlineKeyboardButton(text="💰 Мой баланс", callback_data="my_balance")
                ],
                [
                    InlineKeyboardButton(text="🎮 Мини-игры", callback_data="mini_games"),
                    InlineKeyboardButton(text="🏆 Топ игроков", callback_data="top_players")
                ],
                [InlineKeyboardButton(text="💸 Вывод звезд", callback_data="withdraw"), InlineKeyboardButton(text="❓ FAQ", callback_data="show_faq")]
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

            await message.answer(welcome_text, reply_markup=keyboard)
        else:
            # Update user activity
            db.update_user_activity(user_id)

            buttons = [
                [InlineKeyboardButton(
                    text="📢 Поделиться ссылкой", 
                    switch_inline_query=f"Присоединяйся к боту и зарабатывай звезды! https://t.me/{(await message.bot.get_me()).username}?start={user_id}"
                )],
                [
                    InlineKeyboardButton(text="📝 Список заданий", callback_data="tasks_list"),
                    InlineKeyboardButton(text="💰 Мой баланс", callback_data="my_balance")
                ],
                [
                    InlineKeyboardButton(text="🎮 Мини-игры", callback_data="mini_games"),
                    InlineKeyboardButton(text="🏆 Топ игроков", callback_data="top_players")
                ],
                [InlineKeyboardButton(text="💸 Вывод звезд", callback_data="withdraw"), InlineKeyboardButton(text="❓ FAQ", callback_data="show_faq")]
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

            await message.answer("С возвращением! Выберите действие:", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error in cmd_start: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

# My balance handler
@router.callback_query(F.data == "my_balance")
async def process_my_balance(callback_query: types.CallbackQuery):
    try:
        user_id = callback_query.from_user.id

        stats = db.get_user_stats(user_id)
        settings = db.get_admin_settings()

        if stats and settings:
            stars, completed_tasks, referrals_count = stats
            min_referrals, min_tasks, partner_bonus, _, _ = settings

            balance_text = (
                f"💎 Ваш баланс: {stars} звезд\n\n"
                f"📊 Статистика:\n"
                f"✅ Выполнено заданий: {completed_tasks}/{min_tasks}\n"
                f"👥 Приглашено друзей: {referrals_count}/{min_referrals}\n\n"
            )

            if completed_tasks >= min_tasks and referrals_count >= min_referrals:
                balance_text += "🎉 Вы выполнили все условия для вывода звезд!"
            else:
                balance_text += (
                    f"⚠ Для вывода необходимо:\n"
                    f"- Пригласить {min_referrals} друзей (осталось {max(0, min_referrals - referrals_count)})\n"
                    f"- Выполнить {min_tasks} заданий (осталось {max(0, min_tasks - completed_tasks)})\n"
                )

            buttons = [
                [
                    InlineKeyboardButton(
                        text="👥 Рефералка",
                        switch_inline_query=f"Присоединяйся к боту и зарабатывай звезды! https://t.me/{(await callback_query.bot.get_me()).username}?start={user_id}"
                    )
                ],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

            await callback_query.message.edit_text(balance_text, reply_markup=keyboard)
        else:
            await callback_query.answer("Не удалось загрузить данные. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Error in process_my_balance: {e}")
        await callback_query.answer("Произошла ошибка")

# Tasks list handler
@router.callback_query(F.data == "tasks_list")
async def process_tasks_list(callback_query: types.CallbackQuery):
    try:
        user_id = callback_query.from_user.id
        chat_id = callback_query.message.chat.id

        # Получаем обычные задания из базы данных
        regular_tasks = db.get_active_tasks()

        # Получаем задания от спонсоров Subgram
        from subgram_api import subgram_api
        status, code, message, sponsor_tasks = await subgram_api.get_sponsor_tasks(user_id, chat_id, limit=10)

        tasks_text = "📝 Список доступных заданий:\n\n"
        buttons = []

        # Сначала добавляем задания от спонсоров
        if status == "ok" and sponsor_tasks:
            tasks_text += "🌟 <b>ЗАДАНИЯ ОТ СПОНСОРОВ:</b>\n\n"

            for i, task in enumerate(sponsor_tasks):
                task_id = f"sg_{task.get('id')}"
                description = task.get('title', 'Без описания')
                reward = task.get('reward', 0)
                url = task.get('url', '')

                tasks_text += f"🔸 {description}\n💎 Награда: {reward} руб.\n\n"

                buttons.append([InlineKeyboardButton(
                    text=f"👉 {description[:20]}...", 
                    url=url
                )])

            tasks_text += "➖➖➖➖➖➖➖➖➖➖➖➖\n\n"

        # Больше не добавляем обычные задания из базы данных
        # мы используем только задания от спонсоров Subgram

        # Если нет заданий от спонсоров
        if status != "ok" or not sponsor_tasks:
            tasks_text = "В настоящий момент нет доступных заданий. Пожалуйста, проверьте позже."

        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback_query.message.edit_text(tasks_text, reply_markup=keyboard, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in process_tasks_list: {e}")
        await callback_query.answer("Произошла ошибка при загрузке заданий")

# Complete task handler
@router.callback_query(F.data.startswith("complete_task_"))
async def complete_task(callback_query: types.CallbackQuery):
    try:
        user_id = callback_query.from_user.id
        chat_id = callback_query.message.chat.id
        task_id = int(callback_query.data.split("_")[2])

        # Complete the task
        reward = db.complete_task(user_id, task_id)

        if reward:
            await callback_query.answer(f"Задание выполнено! Получено {reward} звезд")

            # Перенаправляем на обновленный список заданий
            await process_tasks_list(callback_query)
        else:
            await callback_query.answer("Задание уже выполнено или недоступно")
    except Exception as e:
        logger.error(f"Error in complete_task: {e}")
        await callback_query.answer("Произошла ошибка при выполнении задания")

# Mini-games handler
@router.callback_query(F.data == "mini_games")
async def show_mini_games(callback_query: types.CallbackQuery):
    try:
        user_id = callback_query.from_user.id
        daily_games = db.get_user_game_stats(user_id)

        games_text = (
            f"🎮 Мини-игры:\n\n"
            f"Сыграно сегодня: {daily_games}/{GAME_DAILY_LIMIT}\n\n"
            f"Выберите игру:"
        )

        buttons = [
            [
                InlineKeyboardButton(text="🎲 Кости", callback_data="play_dice"),
                InlineKeyboardButton(text="🎰 Слоты", callback_data="play_slots")
            ],
            [InlineKeyboardButton(text="💰 Кража звезд", callback_data="steal_stars")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback_query.message.edit_text(games_text, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in show_mini_games: {e}")
        await callback_query.answer("Произошла ошибка")

# Play dice game
@router.callback_query(F.data == "play_dice")
async def play_dice_game(callback_query: types.CallbackQuery):
    try:
        user_id = callback_query.from_user.id

        can_play, dice_result, reward = await games.play_dice(user_id)

        if not can_play:
            await callback_query.answer("Вы достигли дневного лимита игр. Попробуйте завтра!")
            return

        result_text = (
            f"🎲 Результат броска: {dice_result}\n\n"
            f"{'🎉 Вы выиграли ' + str(reward) + ' звезд!' if reward > 0 else '😔 К сожалению, вы ничего не выиграли'}\n\n"
            f"Сыграно сегодня: {db.get_user_game_stats(user_id)}/{GAME_DAILY_LIMIT}"
        )

        buttons = [
            [
                InlineKeyboardButton(text="🎲 Бросить еще раз", callback_data="play_dice"),
                InlineKeyboardButton(text="🔙 К играм", callback_data="mini_games")
            ],
            [InlineKeyboardButton(text="🔙 В меню", callback_data="main_menu")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback_query.message.edit_text(result_text, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in play_dice_game: {e}")
        await callback_query.answer("Произошла ошибка")

# Play slots game
@router.callback_query(F.data == "play_slots")
async def play_slots_game(callback_query: types.CallbackQuery):
    try:
        user_id = callback_query.from_user.id

        can_play, symbols, reward = await games.play_slots(user_id)

        if not can_play:
            await callback_query.answer("Вы достигли дневного лимита игр. Попробуйте завтра!")
            return

        symbols_str = " ".join(symbols) if symbols else "🎰 🎰 🎰"

        result_text = (
            f"🎰 Результат: {symbols_str}\n\n"
            f"{'🎉 Джекпот! Вы выиграли ' + str(reward) + ' звезд!' if reward > 0 else '😔 К сожалению, вы ничего не выиграли'}\n\n"
            f"Сыграно сегодня: {db.get_user_game_stats(user_id)}/{GAME_DAILY_LIMIT}"
        )

        buttons = [
            [
                InlineKeyboardButton(text="🎰 Крутить еще раз", callback_data="play_slots"),
                InlineKeyboardButton(text="🔙 К играм", callback_data="mini_games")
            ],
            [InlineKeyboardButton(text="🔙 В меню", callback_data="main_menu")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback_query.message.edit_text(result_text, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in play_slots_game: {e}")
        await callback_query.answer("Произошла ошибка")

# Steal stars - select user
@router.callback_query(F.data == "steal_stars")
async def steal_stars_step1(callback_query: types.CallbackQuery):
    try:
        user_id = callback_query.from_user.id

        # Check if user has unlocked the steal feature
        user_stats = db.get_user_stats(user_id)
        settings = db.get_admin_settings()

        if user_stats and settings:
            stars, completed_tasks, referrals_count = user_stats
            _, _, _, _, steal_unlock_tasks = settings

            if completed_tasks < steal_unlock_tasks:
                await callback_query.message.edit_text(
                    f"⚠️ Для доступа к краже звезд необходимо выполнить {steal_unlock_tasks} заданий.\n"
                    f"Выполнено: {completed_tasks}/{steal_unlock_tasks}",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 К играм", callback_data="mini_games")]
                    ])
                )
                return

            # Check daily limit
            daily_games = db.get_user_game_stats(user_id)
            if daily_games >= GAME_DAILY_LIMIT:
                await callback_query.answer("Вы достигли дневного лимита игр. Попробуйте завтра!")
                return

            # Get top users to steal from
            top_users = db.get_top_users(10)

            steal_text = (
                "💰 Кража звезд\n\n"
                "Выберите пользователя, у которого хотите украсть звезды:"
            )

            buttons = []
            for user in top_users:
                victim_id, username, full_name, stars, _, _ = user

                # Skip the current user
                if victim_id == user_id:
                    continue

                display_name = username or full_name or f"User {victim_id}"
                buttons.append([InlineKeyboardButton(
                    text=f"{display_name} ({stars} звезд)", 
                    callback_data=f"steal_from_{victim_id}"
                )])

            buttons.append([InlineKeyboardButton(text="🔙 К играм", callback_data="mini_games")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

            await callback_query.message.edit_text(steal_text, reply_markup=keyboard)
        else:
            await callback_query.answer("Не удалось загрузить данные. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Error in steal_stars_step1: {e}")
        await callback_query.answer("Произошла ошибка")

# Steal stars - execute
@router.callback_query(F.data.startswith("steal_from_"))
async def steal_stars_execute(callback_query: types.CallbackQuery):
    try:
        user_id = callback_query.from_user.id
        victim_id = int(callback_query.data.split("_")[2])

        success, amount = await games.play_steal(user_id, victim_id)

        if success:
            victim = db.get_user(victim_id)
            victim_name = victim[1] or victim[2] or f"User {victim_id}"

            result_text = (
                f"🎭 Кража звезд\n\n"
                f"🎉 Успешно! Вы украли {amount} звезд у пользователя {victim_name}.\n\n"
                f"Сыграно сегодня: {db.get_user_game_stats(user_id)}/{GAME_DAILY_LIMIT}"
            )
        else:
            result_text = (
                f"🎭 Кража звезд\n\n"
                f"😔 Неудача! Вам не удалось украсть звезды.\n\n"
                f"Сыграно сегодня: {db.get_user_game_stats(user_id)}/{GAME_DAILY_LIMIT}"
            )

        buttons = [
            [
                InlineKeyboardButton(text="🔄 Попробовать еще раз", callback_data="steal_stars"),
                InlineKeyboardButton(text="🔙 К играм", callback_data="mini_games")
            ],
            [InlineKeyboardButton(text="🔙 В меню", callback_data="main_menu")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback_query.message.edit_text(result_text, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in steal_stars_execute: {e}")
        await callback_query.answer("Произошла ошибка")

# Leaderboard handler
@router.callback_query(F.data == "top_players")
async def show_top_players(callback_query: types.CallbackQuery):
    try:
        top_users = db.get_top_users()

        if top_users:
            top_text = "🏆 Топ игроков по количеству звезд:\n\n"

            for idx, user in enumerate(top_users, 1):
                user_id, username, full_name, stars, referrals, tasks = user
                display_name = username or full_name or f"User {user_id}"

                top_text += f"{idx}. {display_name} - {stars} звезд\n"

            buttons = [[InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

            await callback_query.message.edit_text(top_text, reply_markup=keyboard)
        else:
            await callback_query.message.edit_text(
                "Пока нет игроков в топе.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
                ])
            )
    except Exception as e:
        logger.error(f"Error in show_top_players: {e}")
        await callback_query.answer("Произошла ошибка")

# Withdrawal handler
@router.callback_query(F.data == "withdraw")
async def withdraw_stars(callback_query: types.CallbackQuery):
    try:
        user_id = callback_query.from_user.id

        user_stats = db.get_user_stats(user_id)
        settings = db.get_admin_settings()

        if user_stats and settings:
            stars, completed_tasks, referrals_count = user_stats
            min_referrals, min_tasks, _, _, _ = settings

            if completed_tasks < min_tasks or referrals_count < min_referrals:
                withdraw_text = (
                    f"⚠️ Вы не выполнили условия для вывода звезд!\n\n"
                    f"Требуется:\n"
                    f"✅ Выполнить {min_tasks} заданий (выполнено: {completed_tasks})\n"
                    f"👥 Пригласить {min_referrals} друзей (приглашено: {referrals_count})\n"
                )

                buttons = [
                    [
                        InlineKeyboardButton(
                            text="👥 Пригласить друзей", 
                            switch_inline_query=f"Присоединяйся к боту и зарабатывай звезды! https://t.me/{(await callback_query.bot.get_me()).username}?start={user_id}"
                        )
                    ],
                    [
                        InlineKeyboardButton(text="📝 К заданиям", callback_data="tasks_list"),
                        InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
                    ]
                ]
                keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

                await callback_query.message.edit_text(withdraw_text, reply_markup=keyboard)
                return

            if stars <= 0:
                await callback_query.message.edit_text(
                    "У вас нет звезд для вывода.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
                    ])
                )
                return

            withdraw_text = (
                f"💸 Вывод звезд\n\n"
                f"Доступно для вывода: {stars} звезд\n\n"
                f"Введите количество звезд для вывода:"
            )

            buttons = [[InlineKeyboardButton(text="🔙 Отмена", callback_data="main_menu")]]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

            await callback_query.message.edit_text(withdraw_text, reply_markup=keyboard)

            # Set state for withdrawal amount
            await callback_query.bot.get_current().dispatcher.get_fsm_context().set_state(
                user_id=user_id, 
                chat_id=callback_query.message.chat.id,
                state=WithdrawStates.waiting_for_withdraw_amount
            )
        else:
            await callback_query.answer("Не удалось загрузить данные. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Error in withdraw_stars: {e}")
        await callback_query.answer("Произошла ошибка")

# Process withdrawal amount
@router.message(WithdrawStates.waiting_for_withdraw_amount)
async def process_withdraw_amount(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id

        # Get current stars
        user_stats = db.get_user_stats(user_id)
        if not user_stats:
            await message.answer(
                "Не удалось загрузить данные. Попробуйте позже.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 В меню", callback_data="main_menu")]
                ])
            )
            await state.clear()
            return

        stars = user_stats[0]

        try:
            amount = int(message.text.strip())

            if amount <= 0:
                await message.answer(
                    "Пожалуйста, введите положительное число звезд для вывода.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Отмена", callback_data="main_menu")]
                    ])
                )
                return

            if amount > stars:
                await message.answer(
                    f"У вас недостаточно звезд. Доступно: {stars}",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Отмена", callback_data="main_menu")]
                    ])
                )
                return

            # Process withdrawal request
            if db.request_withdrawal(user_id, amount):
                await message.answer(
                    f"✅ Запрос на вывод {amount} звезд успешно создан!\n\n"
                    f"Ожидайте обработки администратором.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 В меню", callback_data="main_menu")]
                    ])
                )
                await state.clear()
            else:
                await message.answer(
                    "Произошла ошибка при создании запроса на вывод. Попробуйте позже.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 В меню", callback_data="main_menu")]
                    ])
                )
                await state.clear()

        except ValueError:
            await message.answer(
                "Пожалуйста, введите корректное число звезд для вывода.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Отмена", callback_data="main_menu")]
                ])
            )

    except Exception as e:
        logger.error(f"Error in process_withdraw_amount: {e}")
        await message.answer(
            "Произошла ошибка. Пожалуйста, попробуйте позже.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 В меню", callback_data="main_menu")]
            ])
        )
        await state.clear()

# FAQ handler
@router.callback_query(F.data == "show_faq")
async def show_faq(callback_query: types.CallbackQuery):
    try:
        faq_text = (
            "❓ <b>Часто задаваемые вопросы:</b>\n\n"
            "1️⃣ <b>Как заработать звезды?</b>\n"
            "• Выполняйте задания\n"
            "• Приглашайте друзей\n"
            "• Играйте в мини-игры\n"
            "• Подписывайтесь на каналы\n\n"
            "2️⃣ <b>Как вывести звезды?</b>\n"
            "• Выполните минимальное количество заданий\n"
            "• Пригласите минимальное количество друзей\n"
            "• Нажмите кнопку 'Вывод звезд'\n\n"
            "3️⃣ <b>Что такое Subgram?</b>\n"
            "• Это платформа для обмена звезд на реальные деньги\n"
            "• Можно получать награды за подписку на каналы\n\n"
            "4️⃣ <b>Как пригласить друзей?</b>\n"
            "• Нажмите кнопку 'Поделиться ссылкой'\n"
            "• Отправьте ссылку друзьям\n"
            "• Получайте бонусы за каждого приглашенного"
        )

        buttons = [[InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback_query.message.edit_text(faq_text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in show_faq: {e}")
        await callback_query.answer("Произошла ошибка")