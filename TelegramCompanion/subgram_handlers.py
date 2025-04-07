import datetime
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging
import json
import aiohttp
import os
from typing import Optional, List, Dict, Any

from subgram_api import subgram_api
from keyboards import get_main_menu_keyboard, get_back_button
from database import Database
from config import ADMIN_ID

# URL web-сервера для логирования офферов
WEB_SERVER_URL = os.environ.get('WEB_SERVER_URL', 'http://localhost:5000')

async def log_offer_to_database(user_id, offer_url, offer_id='', channel_name='', reward_amount=10):
    """Логирование оффера в базе данных"""
    try:
        api_url = f"{WEB_SERVER_URL}/api/subgram/log_offer"
        payload = {
            "user_id": user_id,
            "offer_url": offer_url,
            "offer_id": offer_id,
            "channel_name": channel_name,
            "reward_amount": reward_amount
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload) as response:
                if response.status == 200 or response.status == 201:
                    result = await response.json()
                    logger.info(f"Offer logged successfully: {result}")
                    return result
                else:
                    logger.error(f"Failed to log offer: HTTP {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error logging offer to database: {e}")
        return None

async def update_offer_status(user_id, offer_url, status):
    """Обновление статуса оффера в базе данных"""
    try:
        api_url = f"{WEB_SERVER_URL}/api/subgram/update_offer"
        payload = {
            "user_id": user_id,
            "offer_url": offer_url,
            "status": status
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Offer status updated successfully: {result}")
                    return result
                else:
                    logger.error(f"Failed to update offer status: HTTP {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error updating offer status: {e}")
        return None

logger = logging.getLogger(__name__)
router = Router()

db = Database()

class SubgramStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_confirmation = State()

class RequiredChannelStates(StatesGroup):
    waiting_for_channel_id = State()
    waiting_for_channel_name = State()
    waiting_for_stars_reward = State()
    waiting_for_confirmation = State()

@router.callback_query(F.data == "subgram_integration")
async def show_subgram_menu(callback_query: types.CallbackQuery):
    """Show Subgram integration menu"""
    user_id = callback_query.from_user.id

    # Check if user exists in Subgram
    user_info = await subgram_api.get_user_info(user_id)

    # Build button list
    buttons = [
        [
            types.InlineKeyboardButton(
                text="Проверить баланс Subgram", 
                callback_data="check_subgram_balance"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Обменять звезды на баланс Subgram", 
                callback_data="exchange_stars_to_subgram"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Проверить обязательные подписки", 
                callback_data="check_required_subscriptions"
            )
        ]
    ]

    # Add admin buttons if user is admin
    if str(user_id) in ADMIN_ID.split(','):
        buttons.append([
            types.InlineKeyboardButton(
                text="🔧 Управление обязательными подписками", 
                callback_data="manage_required_channels"
            )
        ])

    # Add back button
    buttons.append([
        types.InlineKeyboardButton(
            text="⬅️ Назад", 
            callback_data="main_menu"
        )
    ])

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)

    text = "🔗 Интеграция с Subgram\n\n"

    if user_info:
        text += f"✅ Ваш аккаунт связан с Subgram\n\n"
        # Get Subgram balance if available
        balance = await subgram_api.get_user_balance(user_info.get('id'))
        if balance is not None:
            text += f"💰 Баланс в Subgram: {balance} руб.\n"
    else:
        # Register user in Subgram
        registration = await subgram_api.register_user(
            user_id,
            username=callback_query.from_user.username,
            first_name=callback_query.from_user.first_name,
            last_name=callback_query.from_user.last_name
        )

        if registration and registration.get('success'):
            text += "✅ Ваш аккаунт успешно зарегистрирован в Subgram!\n"
        else:
            text += "❌ Не удалось зарегистрировать аккаунт в Subgram. Пожалуйста, попробуйте позже.\n"

    await callback_query.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "check_subgram_balance")
async def check_subgram_balance(callback_query: types.CallbackQuery):
    """Check Subgram balance"""
    user_id = callback_query.from_user.id

    # Get user info from Subgram
    user_info = await subgram_api.get_user_info(user_id)

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="⬅️ Назад к Subgram", 
                    callback_data="subgram_integration"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="🏠 Главное меню", 
                    callback_data="main_menu"
                )
            ]
        ]
    )

    if user_info:
        subgram_id = user_info.get('id')
        balance = await subgram_api.get_user_balance(subgram_id)

        if balance is not None:
            text = f"💰 Ваш баланс в Subgram: {balance} руб.\n"
        else:
            text = "❌ Не удалось получить информацию о балансе. Пожалуйста, попробуйте позже.\n"
    else:
        text = "❌ Аккаунт не найден в Subgram. Пожалуйста, вернитесь в меню Subgram для регистрации.\n"

    await callback_query.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "exchange_stars_to_subgram")
async def start_exchange_stars(callback_query: types.CallbackQuery, state: FSMContext):
    """Start process of exchanging stars to Subgram balance"""
    user_id = callback_query.from_user.id

    # Get user stats
    user = db.get_user(user_id)
    if not user:
        await callback_query.answer("Ошибка: пользователь не найден", show_alert=True)
        return

    # Check if user has stars to exchange
    if user['stars'] <= 0:
        await callback_query.message.edit_text(
            "❌ У вас нет звезд для обмена.\n"
            "Выполняйте задания и приглашайте друзей, чтобы заработать звезды!",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[[
                    types.InlineKeyboardButton(
                        text="⬅️ Назад", 
                        callback_data="subgram_integration"
                    )
                ]]
            )
        )
        return

    # Set state and ask for amount
    await state.set_state(SubgramStates.waiting_for_amount)

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text=f"{min(10, user['stars'])} ⭐", 
                    callback_data=f"exchange_amount:{min(10, user['stars'])}"
                ),
                types.InlineKeyboardButton(
                    text=f"{min(50, user['stars'])} ⭐", 
                    callback_data=f"exchange_amount:{min(50, user['stars'])}"
                ),
                types.InlineKeyboardButton(
                    text=f"{min(100, user['stars'])} ⭐", 
                    callback_data=f"exchange_amount:{min(100, user['stars'])}"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Максимум", 
                    callback_data=f"exchange_amount:{user['stars']}"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="❌ Отмена", 
                    callback_data="subgram_integration"
                )
            ]
        ]
    )

    await callback_query.message.edit_text(
        f"💫 У вас {user['stars']} звезд\n\n"
        f"Выберите количество звезд для обмена на баланс Subgram.\n"
        f"Курс обмена: 1 звезда = 0.3 рубля",
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("exchange_amount:"), SubgramStates.waiting_for_amount)
async def confirm_exchange(callback_query: types.CallbackQuery, state: FSMContext):
    """Confirm exchange amount"""
    amount = int(callback_query.data.split(":")[1])
    user_id = callback_query.from_user.id

    # Store amount in state
    await state.update_data(amount=amount)

    # Calculate Subgram amount (conversion rate)
    subgram_amount = amount * 0.3  # 1 star = 0.3 rub

    # Set confirmation state
    await state.set_state(SubgramStates.waiting_for_confirmation)

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="✅ Подтвердить", 
                    callback_data="confirm_exchange"
                ),
                types.InlineKeyboardButton(
                    text="❌ Отмена", 
                    callback_data="cancel_exchange"
                )
            ]
        ]
    )

    await callback_query.message.edit_text(
        f"⚠️ Подтверждение обмена\n\n"
        f"Вы собираетесь обменять {amount} звезд на {subgram_amount:.2f} руб. на вашем балансе Subgram.\n\n"
        f"Подтвердите операцию:",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "confirm_exchange", SubgramStates.waiting_for_confirmation)
async def process_exchange(callback_query: types.CallbackQuery, state: FSMContext):
    """Process the exchange of stars to Subgram balance"""
    user_id = callback_query.from_user.id

    # Get data from state
    state_data = await state.get_data()
    amount = state_data.get("amount", 0)

    # Get user from database
    user = db.get_user(user_id)
    if not user:
        await callback_query.answer("Ошибка: пользователь не найден", show_alert=True)
        await state.clear()
        return

    # Check if user has enough stars
    if user['stars'] < amount:
        await callback_query.message.edit_text(
            "❌ У вас недостаточно звезд для этого обмена.",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[[
                    types.InlineKeyboardButton(
                        text="⬅️ Назад", 
                        callback_data="subgram_integration"
                    )
                ]]
            )
        )
        await state.clear()
        return

    # Get user info from Subgram
    user_info = await subgram_api.get_user_info(user_id)

    if not user_info:
        await callback_query.message.edit_text(
            "❌ Ваш аккаунт не найден в Subgram. Пожалуйста, вернитесь в меню Subgram.",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[[
                    types.InlineKeyboardButton(
                        text="⬅️ Назад к Subgram", 
                        callback_data="subgram_integration"
                    )
                ]]
            )
        )
        await state.clear()
        return

    # Calculate Subgram amount
    subgram_amount = amount * 0.3  # 1 star = 0.3 rub

    # Create transaction in Subgram
    transaction = await subgram_api.create_transaction(
        user_info.get('id'),
        subgram_amount,
        f"Обмен {amount} звезд из Stars Bot"
    )

    if transaction and transaction.get('success'):
        # Deduct stars from user
        db.update_user_stars(user_id, -amount)

        # Update completed tasks counter and user activity
        db.cursor.execute('''
            UPDATE users 
            SET completed_tasks = completed_tasks + 1,
                last_activity = datetime('now')
            WHERE user_id = ?
        ''', (user_id,))
        db.conn.commit()

        # Sync with PostgreSQL through the web API
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{WEB_SERVER_URL}/api/users/update_tasks", 
                    json={"user_id": user_id}) as response:
                    if response.status != 200:
                        logger.error("Failed to sync task completion with web API")
        except Exception as e:
            logger.error(f"Error syncing task completion: {e}")

        # Log exchange in the database
        db.log_subgram_exchange(user_id, amount, subgram_amount, 'completed')
        logger.info(f"Subgram exchange logged: User {user_id} exchanged {amount} stars for {subgram_amount} rubles")

        await callback_query.message.edit_text(
            f"✅ Обмен успешно выполнен!\n\n"
            f"Вы обменяли {amount} звезд на {subgram_amount:.2f} руб.\n"
            f"Средства зачислены на ваш баланс Subgram.",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        types.InlineKeyboardButton(
                            text="⬅️ Назад к Subgram", 
                            callback_data="subgram_integration"
                        )
                    ],
                    [
                        types.InlineKeyboardButton(
                            text="🏠 Главное меню", 
                            callback_data="main_menu"
                        )
                    ]
                ]
            )
        )
    else:
        await callback_query.message.edit_text(
            "❌ Ошибка при выполнении транзакции. Пожалуйста, попробуйте позже.",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[[
                    types.InlineKeyboardButton(
                        text="⬅️ Назад", 
                        callback_data="subgram_integration"
                    )
                ]]
            )
        )

    # Clear state
    await state.clear()

@router.callback_query(F.data == "cancel_exchange")
async def cancel_exchange(callback_query: types.CallbackQuery, state: FSMContext):
    """Cancel the exchange process"""
    await state.clear()
    await callback_query.message.edit_text(
        "❌ Обмен отменен.",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[[
                types.InlineKeyboardButton(
                    text="⬅️ Назад", 
                    callback_data="subgram_integration"
                )
            ]]
        )
    )

@router.callback_query(F.data == "check_required_subscriptions")
async def check_required_subscriptions(callback_query: types.CallbackQuery):
    """Check if user is subscribed to all required channels"""
    user_id = callback_query.from_user.id

    # Get user info from Subgram
    user_info = await subgram_api.get_user_info(user_id)
    if not user_info:
        await callback_query.message.edit_text(
            "❌ Ваш аккаунт не найден в Subgram. Пожалуйста, вернитесь в меню Subgram для регистрации.",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[[
                    types.InlineKeyboardButton(
                        text="⬅️ Назад", 
                        callback_data="subgram_integration"
                    )
                ]]
            )
        )
        return

    # Get list of required channels
    required_channels = await subgram_api.get_required_channels()
    if not required_channels or not isinstance(required_channels, list):
        await callback_query.message.edit_text(
            "❌ Не удалось получить список обязательных подписок. Пожалуйста, попробуйте позже.",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[[
                    types.InlineKeyboardButton(
                        text="⬅️ Назад", 
                        callback_data="subgram_integration"
                    )
                ]]
            )
        )
        return

    # Check subscriptions and build message
    text = "📢 Проверка обязательных подписок:\n\n"

    if not required_channels:
        text += "✅ Нет обязательных подписок.\n"
    else:
        total_channels = len(required_channels)
        subscribed_count = 0
        buttons = []

        # Get previously rewarded channels
        rewarded_channels = db.get_user_subscription_rewards(user_id)
        rewarded_channel_ids = [item[0] for item in rewarded_channels] if rewarded_channels else []

        for channel in required_channels:
            channel_id = channel.get('channel_id')
            channel_name = channel.get('channel_name', 'Неизвестный канал')
            stars_reward = channel.get('stars_reward', 0)

            is_subscribed = await subgram_api.check_subscription(user_info.get('id'), channel_id)

            if is_subscribed:
                subscribed_count += 1
                already_rewarded = channel_id in rewarded_channel_ids

                if already_rewarded:
                    text += f"✅ {channel_name} - Вы подписаны (награда получена)\n"
                else:
                    text += f"✅ {channel_name} - Вы подписаны! Нажмите, чтобы получить {stars_reward} звезд\n"
                    # Add claim reward button
                    buttons.append([
                        types.InlineKeyboardButton(
                            text=f"💰 Получить {stars_reward} звезд за {channel_name}", 
                            callback_data=f"claim_subscription_reward:{channel_id}:{channel_name}:{stars_reward}"
                        )
                    ])
            else:
                text += f"❌ {channel_name} - Не подписаны (награда: {stars_reward} звезд)\n"
                # Add link to subscribe
                text += f"👉 https://t.me/{channel_id.replace('@', '')}\n\n"

        text += f"\nИтого: {subscribed_count}/{total_channels} подписок\n"

        if subscribed_count == total_channels:
            text += "\n🎉 Вы подписаны на все каналы! Заберите ваши награды 👇"

    # Add button to check again
    check_button = [
        types.InlineKeyboardButton(
            text="🔄 Проверить снова", 
            callback_data="check_required_subscriptions"
        )
    ]
    back_button = [
        types.InlineKeyboardButton(
            text="⬅️ Назад", 
            callback_data="subgram_integration"
        )
    ]

    # Build final keyboard
    all_buttons = buttons + [check_button, back_button]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=all_buttons)

    await callback_query.message.edit_text(text, reply_markup=keyboard, disable_web_page_preview=True)

@router.callback_query(F.data.startswith("claim_subscription_reward:"))
async def claim_subscription_reward(callback_query: types.CallbackQuery):
    """Claim reward for channel subscription"""
    user_id = callback_query.from_user.id
    parts = callback_query.data.split(":")

    if len(parts) < 4:
        await callback_query.answer("Ошибка в данных. Пожалуйста, попробуйте снова.", show_alert=True)
        return

    channel_id = parts[1]
    channel_name = parts[2]
    stars_reward = int(parts[3])

    # Get user info from Subgram
    user_info = await subgram_api.get_user_info(user_id)
    if not user_info:
        await callback_query.answer("Ваш аккаунт не найден в Subgram.", show_alert=True)
        return

    # Verify subscription
    is_subscribed = await subgram_api.check_subscription(user_info.get('id'), channel_id)
    if not is_subscribed:
        await callback_query.answer(
            f"Вы не подписаны на канал {channel_name}. Пожалуйста, подпишитесь, чтобы получить награду.",
            show_alert=True
        )
        return

    # Log reward in database
    success = db.log_subscription_reward(user_id, channel_id, channel_name, stars_reward)

    if success:
        await callback_query.answer(
            f"✅ Вы получили {stars_reward} звезд за подписку на {channel_name}!",
            show_alert=True
        )
        # Refresh the subscriptions list
        await check_required_subscriptions(callback_query)
    else:
        # Already rewarded
        await callback_query.answer(
            f"Вы уже получили награду за подписку на этот канал.",
            show_alert=True
        )

@router.callback_query(F.data == "manage_required_channels")
async def manage_required_channels(callback_query: types.CallbackQuery):
    """Admin function to manage required channels"""
    user_id = callback_query.from_user.id

    # Check if user is admin
    if str(user_id) not in ADMIN_ID.split(','):
        await callback_query.answer("❌ У вас нет доступа к этой функции", show_alert=True)
        return

    # Get list of required channels
    required_channels = await subgram_api.get_required_channels()

    text = "🔧 Управление обязательными подписками:\n\n"

    if not required_channels or not isinstance(required_channels, list):
        text += "Список пуст или произошла ошибка при получении данных.\n"
    else:
        for i, channel in enumerate(required_channels, 1):
            channel_id = channel.get('channel_id', 'Unknown')
            channel_name = channel.get('channel_name', 'Неизвестный канал')
            stars_reward = channel.get('stars_reward', 0)

            text += f"{i}. {channel_name} ({channel_id})\n"
            text += f"   Награда: {stars_reward} звезд\n\n"

    # Create keyboard
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="➕ Добавить канал", 
                    callback_data="add_required_channel"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="❌ Удалить канал", 
                    callback_data="remove_required_channel"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="⬅️ Назад", 
                    callback_data="subgram_integration"
                )
            ]
        ]
    )

    await callback_query.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "add_required_channel")
async def start_add_channel(callback_query: types.CallbackQuery, state: FSMContext):
    """Start process of adding a required channel"""
    user_id = callback_query.from_user.id

    # Check if user is admin
    if str(user_id) not in ADMIN_ID.split(','):
        await callback_query.answer("❌ У вас нет доступа к этой функции", show_alert=True)
        return

    await state.set_state(RequiredChannelStates.waiting_for_channel_id)

    await callback_query.message.edit_text(
        "Введите ID канала в формате @channel_id:",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[[
                types.InlineKeyboardButton(
                    text="❌ Отмена", 
                    callback_data="manage_required_channels"
                )
            ]]
        )
    )

@router.message(RequiredChannelStates.waiting_for_channel_id)
async def process_channel_id(message: types.Message, state: FSMContext):
    """Process channel ID input"""
    channel_id = message.text.strip()

    # Validate channel_id format
    if not channel_id.startswith('@'):
        await message.reply(
            "❌ ID канала должен начинаться с символа @\n"
            "Пожалуйста, введите ID канала в формате @channel_id:",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[[
                    types.InlineKeyboardButton(
                        text="❌ Отмена", 
                        callback_data="manage_required_channels"
                    )
                ]]
            )
        )
        return

    # Save channel ID to state
    await state.update_data(channel_id=channel_id)

    # Move to next state
    await state.set_state(RequiredChannelStates.waiting_for_channel_name)

    await message.reply(
        "Введите название канала (будет отображаться пользователям):",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[[
                types.InlineKeyboardButton(
                    text="❌ Отмена", 
                    callback_data="manage_required_channels"
                )
            ]]
        )
    )

@router.message(RequiredChannelStates.waiting_for_channel_name)
async def process_channel_name(message: types.Message, state: FSMContext):
    """Process channel name input"""
    channel_name = message.text.strip()

    # Save channel name to state
    await state.update_data(channel_name=channel_name)

    # Move to next state
    await state.set_state(RequiredChannelStates.waiting_for_stars_reward)

    await message.reply(
        "Введите количество звезд за подписку (целое число):",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[[
                types.InlineKeyboardButton(
                    text="❌ Отмена", 
                    callback_data="manage_required_channels"
                )
            ]]
        )
    )

@router.message(RequiredChannelStates.waiting_for_stars_reward)
async def process_stars_reward(message: types.Message, state: FSMContext):
    """Process stars reward input"""
    try:
        stars_reward = int(message.text.strip())
        if stars_reward < 0:
            raise ValueError("Negative value")
    except ValueError:
        await message.reply(
            "❌ Пожалуйста, введите положительное целое число:",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[[
                    types.InlineKeyboardButton(
                        text="❌ Отмена", 
                        callback_data="manage_required_channels"
                    )
                ]]
            )
        )
        return

    # Save stars reward to state
    await state.update_data(stars_reward=stars_reward)

    # Get all data and ask for confirmation
    data = await state.get_data()
    channel_id = data.get('channel_id')
    channel_name = data.get('channel_name')

    await state.set_state(RequiredChannelStates.waiting_for_confirmation)

    await message.reply(
        f"⚠️ Подтвердите добавление канала:\n\n"
        f"ID: {channel_id}\n"
        f"Название: {channel_name}\n"
        f"Награда: {stars_reward} звезд\n\n"
        f"Все верно?",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="✅ Подтвердить", 
                        callback_data="confirm_add_channel"
                    ),
                    types.InlineKeyboardButton(
                        text="❌ Отмена", 
                        callback_data="manage_required_channels"
                    )
                ]
            ]
        )
    )

@router.callback_query(F.data == "confirm_add_channel", RequiredChannelStates.waiting_for_confirmation)
async def confirm_add_channel(callback_query: types.CallbackQuery, state: FSMContext):
    """Confirm adding a new required channel"""
    # Get data from state
    data = await state.get_data()
    channel_id = data.get('channel_id')
    channel_name = data.get('channel_name')
    stars_reward = data.get('stars_reward')

    # Add channel to required list
    result = await subgram_api.add_required_channel(channel_id, channel_name, stars_reward)

    if result and result.get('success'):
        await callback_query.message.edit_text(
            f"✅ Канал {channel_name} успешно добавлен в список обязательных подписок!",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[[
                    types.InlineKeyboardButton(
                        text="⬅️ Назад к управлению", 
                        callback_data="manage_required_channels"
                    )
                ]]
            )
        )
    else:
        await callback_query.message.edit_text(
            "❌ Ошибка при добавлении канала. Пожалуйста, попробуйте позже.",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[[
                    types.InlineKeyboardButton(
                        text="⬅️ Назад", 
                        callback_data="manage_required_channels"
                    )
                ]]
            )
        )

    # Clear state
    await state.clear()

@router.callback_query(F.data == "remove_required_channel")
async def show_remove_channel_options(callback_query: types.CallbackQuery):
    """Show options to remove a required channel"""
    user_id = callback_query.from_user.id

    # Check if user is admin
    if str(user_id) not in ADMIN_ID.split(','):
        await callback_query.answer("❌ У вас нет доступа к этой функции", show_alert=True)
        return

    # Get list of required channels
    required_channels = await subgram_api.get_required_channels()

    if not required_channels or not isinstance(required_channels, list) or len(required_channels) == 0:
        await callback_query.message.edit_text(
            "❌ Список обязательных подписок пуст.",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[[
                    types.InlineKeyboardButton(
                        text="⬅️ Назад", 
                        callback_data="manage_required_channels"
                    )
                ]]
            )
        )
        return

    # Create keyboard with channel options
    buttons = []
    for channel in required_channels:
        channel_id = channel.get('channel_id')
        channel_name = channel.get('channel_name', 'Неизвестный канал')

        buttons.append([
            types.InlineKeyboardButton(
                text=f"❌ {channel_name}", 
                callback_data=f"remove_channel:{channel_id}"
            )
        ])

    # Add back button
    buttons.append([
        types.InlineKeyboardButton(
            text="⬅️ Назад", 
            callback_data="manage_required_channels"
        )
    ])

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback_query.message.edit_text(
        "Выберите канал для удаления из списка обязательных подписок:",
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("remove_channel:"))
async def remove_channel(callback_query: types.CallbackQuery):
    """Remove a channel from required subscriptions"""
    user_id = callback_query.from_user.id

    # Check if user is admin
    if str(user_id) not in ADMIN_ID.split(','):
        await callback_query.answer("❌ У вас нет доступа к этой функции", show_alert=True)
        return

    # Get channel ID from callback data
    channel_id = callback_query.data.split(":")[1]

    # Remove channel from required list
    result = await subgram_api.remove_required_channel(channel_id)

    if result and result.get('success'):
        await callback_query.message.edit_text(
            f"✅ Канал {channel_id} успешно удален из списка обязательных подписок!",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[[
                    types.InlineKeyboardButton(
                        text="⬅️Назад к управлению", 
                        callback_data="manage_required_channels"
                    )
                ]]
            )
        )
    else:
        await callback_query.message.edit_text(
            "❌ Ошибка при удалении канала. Пожалуйста, попробуйте позже.",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[[
                    types.InlineKeyboardButton(
                        text="⬅️ Назад", 
                        callback_data="manage_required_channels"
                    )
                ]]
            )
        )

# Обработчик для callback-запросов, связанных с обязательными подписками в формате Subgram
@router.callback_query(F.data.startswith("subgram"))
async def subgram_callback_query(callback_query: types.CallbackQuery):
    """Обработка callback-запросов от блока обязательной подписки Subgram"""
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id

    if callback_query.data == "subgram-op":
        # Получаем дополнительные данные о пользователе
        first_name = callback_query.from_user.first_name
        language_code = callback_query.from_user.language_code
        is_premium = callback_query.from_user.is_premium

        # Запрос к API Subgram для проверки подписок
        status, code, message, links = await subgram_api.request_op(
            user_id, 
            chat_id,
            first_name=first_name,
            language_code=language_code,
            is_premium=is_premium
        )

        # Логируем запрос оффера в базе данных через API
        if links and isinstance(links, list) and len(links) > 0:
            for link_data in links:
                offer_url = link_data.get('url', '')
                channel_name = link_data.get('name', '')
                # Используем 10 звезд как стандартную награду, если не указано иное
                reward_amount = link_data.get('stars_reward', 10)
                offer_id = str(link_data.get('id', ''))

                if offer_url:
                    try:
                        # Логируем оффер в базе данных
                        await log_offer_to_database(
                            user_id=user_id,
                            offer_url=offer_url,
                            offer_id=offer_id,
                            channel_name=channel_name,
                            reward_amount=reward_amount
                        )
                        logger.info(f"Subgram offer logged: User {user_id}, Channel {channel_name}, URL {offer_url}")
                    except Exception as e:
                        logger.error(f"Error logging Subgram offer: {e}")

        if status == 'ok' and code == 200:
            # Пользователь подписан на все каналы
            # Выдаем награду и показываем сообщение
            user_data = db.get_user(user_id)
            reward_stars = 10  # Базовая награда за все подписки

            # Увеличиваем количество звезд
            db.update_user_stars(user_id, reward_stars)

            # Получаем обновленные данные пользователя
            updated_user_data = db.get_user(user_id)

            # Обновляем статус офферов в базе данных на 'completed'
            if links and isinstance(links, list):
                for link_data in links:
                    offer_url = link_data.get('url', '')
                    if offer_url:
                        try:
                            await update_offer_status(user_id, offer_url, 'completed')
                            logger.info(f"Offer status updated to completed: User {user_id}, URL {offer_url}")
                        except Exception as e:
                            logger.error(f"Error updating offer status: {e}")

            await callback_query.message.edit_text(
                f"✅ Спасибо за подписку! Вы получили {reward_stars} звезд!\n\n"
                f"Текущий баланс: {updated_user_data[4]} звезд",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[[
                        types.InlineKeyboardButton(
                            text="🏠 Главное меню", 
                            callback_data="main_menu"
                        )
                    ]]
                )
            )
        elif status == 'ok':
            # Пользователь может продолжить, но подписки не подтверждены
            await callback_query.message.edit_text(
                "✅ Спасибо за подписку! Вы можете продолжить пользоваться нашим ботом.",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[[
                        types.InlineKeyboardButton(
                            text="🏠 Главное меню", 
                            callback_data="main_menu"
                        )
                    ]]
                )
            )
        elif status == 'warning' and links:
            # Пользователь не подписан на один или несколько каналов
            # Показываем список каналов для подписки
            text = "⚠️ Для продолжения необходимо подписаться на следующие каналы:\n\n"

            keyboard = []
            for i, link in enumerate(links, 1):
                text += f"{i}. {link}\n"
                keyboard.append([
                    types.InlineKeyboardButton(
                        text=f"Канал {i}", 
                        url=link
                    )
                ])

            text += "\nПосле подписки на все каналы нажмите кнопку 'Проверить подписки'."

            keyboard.append([
                types.InlineKeyboardButton(
                    text="🔄 Проверить подписки", 
                    callback_data="subgram-op"
                )
            ])

            await callback_query.message.edit_text(
                text,
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard),
                disable_web_page_preview=True
            )
        elif status == 'gender':
            # Запрос пола пользователя для более релевантных предложений
            await callback_query.message.edit_text(
                "📊 Для более персонализированных предложений, пожалуйста, укажите ваш пол:",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            types.InlineKeyboardButton(
                                text="♂️ Мужской", 
                                callback_data="subgram_gender_male"
                            )
                        ],
                        [
                            types.InlineKeyboardButton(
                                text="♀️ Женский", 
                                callback_data="subgram_gender_female"
                            )
                        ]
                    ]
                )
            )
        else:
            # Ошибка или другой статус
            logger.warning(f"Unexpected Subgram API response: {status}, {code}, {message}")
            await callback_query.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

    elif callback_query.data.startswith("subgram_gender_"):
        # Обработка выбора пола пользователя
        gender = callback_query.data.split("_")[2]  # Получаем значение пола из callback_data

        # Получаем дополнительные данные о пользователе
        first_name = callback_query.from_user.first_name
        language_code = callback_query.from_user.language_code
        is_premium = callback_query.from_user.is_premium

        # Запрос к API Subgram с указанием пола
        status, code, message, links = await subgram_api.request_op(
            user_id, 
            chat_id,
            gender=gender,
            first_name=first_name,
            language_code=language_code,
            is_premium=is_premium
        )

        # Логируем запрос оффера в базе данных через API
        if links and isinstance(links, list) and len(links) > 0:
            for link_data in links:
                offer_url = link_data.get('url', '')
                channel_name = link_data.get('name', '')
                # Используем 10 звезд как стандартную награду, если не указано иное
                reward_amount = link_data.get('stars_reward', 10)
                offer_id = str(link_data.get('id', ''))

                if offer_url:
                    try:
                        # Логируем оффер в базе данных
                        await log_offer_to_database(
                            user_id=user_id,
                            offer_url=offer_url,
                            offer_id=offer_id,
                            channel_name=channel_name,
                            reward_amount=reward_amount
                        )
                        logger.info(f"Subgram offer logged (gender={gender}): User {user_id}, Channel {channel_name}, URL {offer_url}")
                    except Exception as e:
                        logger.error(f"Error logging Subgram offer (gender={gender}): {e}")

        # Обработка ответа аналогично предыдущему случаю
        if status == 'ok' and code == 200:
            # Пользователь подписан на все каналы
            user_data = db.get_user(user_id)
            reward_stars = 10
            db.update_user_stars(user_id, reward_stars)

            # Получаем обновленные данные пользователя
            updated_user_data = db.get_user(user_id)

            # Обновляем статус офферов в базе данных на 'completed'
            if links and isinstance(links, list):
                for link_data in links:
                    offer_url = link_data.get('url', '')
                    if offer_url:
                        try:
                            await update_offer_status(user_id, offer_url, 'completed')
                            logger.info(f"Offer status updated to completed (gender={gender}): User {user_id}, URL {offer_url}")
                        except Exception as e:
                            logger.error(f"Error updating offer status (gender={gender}): {e}")

            await callback_query.message.edit_text(
                f"✅ Спасибо за подписку! Вы получили {reward_stars} звезд!\n\n"
                f"Текущий баланс: {updated_user_data[4]} звезд",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[[
                        types.InlineKeyboardButton(
                            text="🏠 Главное меню", 
                            callback_data="main_menu"
                        )
                    ]]
                )
            )
        elif status == 'ok':
            await callback_query.message.edit_text(
                "✅ Спасибо за подписку! Вы можете продолжить пользоваться нашим ботом.",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[[
                        types.InlineKeyboardButton(
                            text="🏠 Главное меню", 
                            callback_data="main_menu"
                        )
                    ]]
                )
            )
        elif status == 'warning' and links:
            text = "⚠️ Для продолжения необходимо подписаться на следующие каналы:\n\n"

            keyboard = []
            for i, link in enumerate(links, 1):
                text += f"{i}. {link}\n"
                keyboard.append([
                    types.InlineKeyboardButton(
                        text=f"Канал {i}", 
                        url=link
                    )
                ])

            text += "\nПосле подписки на все каналы нажмите кнопку 'Проверить подписки'."

            keyboard.append([
                types.InlineKeyboardButton(
                    text="🔄 Проверить подписки", 
                    callback_data=f"subgram_gender_{gender}"
                )
            ])

            await callback_query.message.edit_text(
                text,
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard),
                disable_web_page_preview=True
            )
        else:
            logger.warning(f"Unexpected Subgram API response: {status}, {code}, {message}")
            await callback_query.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

def register_handlers(dp):
    dp.include_router(router)