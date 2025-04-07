import random
import logging
import asyncio
from aiogram import types, Bot, F, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from models import GameStates
from database import get_user_stats, update_game_stats
from keyboards import (
    get_games_keyboard, get_bet_keyboard, get_number_guess_keyboard, get_back_button
)

logger = logging.getLogger(__name__)

# Register game handlers
def register_handlers(dp: Dispatcher, bot: Bot):
    # Games menu
    dp.callback_query.register(show_games_menu, F.data == "mini_games")
    
    # Dice game
    dp.callback_query.register(show_dice_game, F.data == "game_dice")
    dp.callback_query.register(process_dice_bet, F.data.startswith("bet_"))
    dp.callback_query.register(play_dice_game, F.data == "play_dice")
    
    # Number guess game
    dp.callback_query.register(show_number_game, F.data == "game_number")
    dp.callback_query.register(process_number_bet, F.data.startswith("bet_"), GameStates.number_guess_bet)
    dp.callback_query.register(process_number_guess, F.data.startswith("guess_"), GameStates.number_guess_playing)
    
    # Slot machine game
    dp.callback_query.register(show_slot_machine, F.data == "game_slot")
    dp.callback_query.register(process_slot_bet, F.data.startswith("bet_"), GameStates.slot_machine_bet)
    dp.callback_query.register(play_slot_machine, F.data == "play_slot")
    
    # Darts game
    dp.callback_query.register(show_darts_game, F.data == "game_darts")
    dp.callback_query.register(process_darts_bet, F.data.startswith("bet_"))
    dp.callback_query.register(play_darts_game, F.data == "play_darts")
    
    logger.info("Game handlers registered")

# Games menu handler
async def show_games_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🎮 <b>Мини-игры</b>\n\n"
        "Выберите игру, чтобы заработать дополнительные звезды:",
        reply_markup=get_games_keyboard()
    )
    await callback.answer()

# Dice game handlers
async def show_dice_game(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🎲 <b>Игра в кубики</b>\n\n"
        "Правила:\n"
        "- Вы и бот бросаете кубики\n"
        "- Если у вас выпало больше, вы выигрываете сумму ставки\n"
        "- Если у бота выпало больше, вы теряете ставку\n"
        "- При равном счете ставка возвращается\n\n"
        "Выберите сумму ставки:",
        reply_markup=get_bet_keyboard()
    )
    await callback.answer()

async def process_dice_bet(callback: types.CallbackQuery):
    try:
        bet = int(callback.data.split("_")[1])
        user_id = callback.from_user.id
        
        # Check if user has enough stars
        user_stats = get_user_stats(user_id)
        if not user_stats or user_stats[0] < bet:
            await callback.answer("У вас недостаточно звезд для этой ставки!", show_alert=True)
            return
        
        # Show play button
        buttons = [
            [InlineKeyboardButton(text="🎲 Бросить кубики", callback_data="play_dice")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="game_dice")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            f"🎲 <b>Игра в кубики</b>\n\n"
            f"Ваша ставка: {bet} звезд\n\n"
            f"Нажмите кнопку, чтобы бросить кубики!",
            reply_markup=keyboard
        )
        
        # Save bet in storage
        await callback.bot.fsm_storage.set_data(
            bot=callback.bot,
            chat_id=callback.message.chat.id,
            user_id=user_id,
            data={"dice_bet": bet}
        )
        
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in process_dice_bet: {e}")
        await callback.answer("Произошла ошибка при обработке ставки")

async def play_dice_game(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id
        
        # Get the bet from storage
        data = await callback.bot.fsm_storage.get_data(
            bot=callback.bot,
            chat_id=callback.message.chat.id,
            user_id=user_id
        )
        bet = data.get("dice_bet", 0)
        
        if bet <= 0:
            await callback.answer("Ставка не найдена, начните игру заново", show_alert=True)
            return
        
        # User's roll
        user_dice = await callback.message.answer_dice(emoji="🎲")
        user_value = user_dice.dice.value
        await asyncio.sleep(2)  # Wait for animation
        
        # Bot's roll
        bot_dice = await callback.message.answer_dice(emoji="🎲")
        bot_value = bot_dice.dice.value
        await asyncio.sleep(2)  # Wait for animation
        
        # Determine the winner
        result_text = ""
        stars_won = 0
        
        if user_value > bot_value:
            result_text = f"🎉 <b>Вы выиграли!</b> Получено {bet} звезд!"
            stars_won = bet
        elif user_value < bot_value:
            result_text = f"😔 <b>Вы проиграли.</b> Потеряно {bet} звезд."
            stars_won = -bet
        else:
            result_text = f"🤝 <b>Ничья!</b> Ваша ставка возвращена."
            stars_won = 0
        
        # Update game stats in database
        update_game_stats(user_id, "dice", stars_won)
        
        # Send result message
        await callback.message.answer(
            f"🎲 <b>Результаты игры в кубики</b>\n\n"
            f"Ваш бросок: {user_value}\n"
            f"Бросок бота: {bot_value}\n\n"
            f"{result_text}",
            reply_markup=get_games_keyboard()
        )
        
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in play_dice_game: {e}")
        await callback.answer("Произошла ошибка при игре в кубики")

# Number guess game handlers
async def show_number_game(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(GameStates.number_guess_bet)
    await callback.message.edit_text(
        "🔢 <b>Угадай число</b>\n\n"
        "Правила:\n"
        "- Бот загадывает число от 1 до 10\n"
        "- Если вы угадаете, то получите ставку x5\n"
        "- Если не угадаете, то потеряете ставку\n\n"
        "Выберите сумму ставки:",
        reply_markup=get_bet_keyboard()
    )
    await callback.answer()

async def process_number_bet(callback: types.CallbackQuery, state: FSMContext):
    try:
        bet = int(callback.data.split("_")[1])
        user_id = callback.from_user.id
        
        # Check if user has enough stars
        user_stats = get_user_stats(user_id)
        if not user_stats or user_stats[0] < bet:
            await callback.answer("У вас недостаточно звезд для этой ставки!", show_alert=True)
            return
        
        # Save bet and set state
        await state.update_data(number_bet=bet)
        await state.set_state(GameStates.number_guess_playing)
        
        await callback.message.edit_text(
            f"🔢 <b>Угадай число</b>\n\n"
            f"Ваша ставка: {bet} звезд\n\n"
            f"Бот загадал число от 1 до 10.\n"
            f"Выберите число:",
            reply_markup=get_number_guess_keyboard()
        )
        
        # Generate random number and save
        bot_number = random.randint(1, 10)
        await state.update_data(bot_number=bot_number)
        
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in process_number_bet: {e}")
        await state.clear()
        await callback.answer("Произошла ошибка при обработке ставки")

async def process_number_guess(callback: types.CallbackQuery, state: FSMContext):
    try:
        user_id = callback.from_user.id
        user_guess = int(callback.data.split("_")[1])
        
        # Get stored data
        data = await state.get_data()
        bet = data.get("number_bet", 0)
        bot_number = data.get("bot_number", 0)
        
        if bet <= 0 or bot_number <= 0:
            await callback.answer("Данные игры не найдены, начните заново", show_alert=True)
            await state.clear()
            return
        
        # Determine result
        result_text = ""
        stars_won = 0
        
        if user_guess == bot_number:
            win_amount = bet * 5
            result_text = f"🎉 <b>Вы угадали!</b> Получено {win_amount} звезд!"
            stars_won = win_amount
        else:
            result_text = f"😔 <b>Вы не угадали.</b> Потеряно {bet} звезд.\nЗагаданное число: {bot_number}"
            stars_won = -bet
        
        # Update game stats
        update_game_stats(user_id, "number_guess", stars_won)
        
        # Send result
        await callback.message.edit_text(
            f"🔢 <b>Результаты игры «Угадай число»</b>\n\n"
            f"Загаданное число: {bot_number}\n"
            f"Ваше число: {user_guess}\n\n"
            f"{result_text}",
            reply_markup=get_games_keyboard()
        )
        
        # Clear state
        await state.clear()
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in process_number_guess: {e}")
        await state.clear()
        await callback.answer("Произошла ошибка при обработке выбора числа")

# Slot machine game handlers
async def show_slot_machine(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(GameStates.slot_machine_bet)
    await callback.message.edit_text(
        "🎰 <b>Слот-машина</b>\n\n"
        "Правила:\n"
        "- Вы крутите слот-машину с тремя барабанами\n"
        "- 2 одинаковых символа: выигрыш x2\n"
        "- 3 одинаковых символа: выигрыш x10\n"
        "- 3 семерки (777): джекпот x50\n\n"
        "Выберите сумму ставки:",
        reply_markup=get_bet_keyboard()
    )
    await callback.answer()

async def process_slot_bet(callback: types.CallbackQuery, state: FSMContext):
    try:
        bet = int(callback.data.split("_")[1])
        user_id = callback.from_user.id
        
        # Check if user has enough stars
        user_stats = get_user_stats(user_id)
        if not user_stats or user_stats[0] < bet:
            await callback.answer("У вас недостаточно звезд для этой ставки!", show_alert=True)
            return
        
        # Save bet
        await state.update_data(slot_bet=bet)
        
        # Show play button
        buttons = [
            [InlineKeyboardButton(text="🎰 Крутить", callback_data="play_slot")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="game_slot")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            f"🎰 <b>Слот-машина</b>\n\n"
            f"Ваша ставка: {bet} звезд\n\n"
            f"Нажмите кнопку, чтобы крутить слот-машину!",
            reply_markup=keyboard
        )
        
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in process_slot_bet: {e}")
        await state.clear()
        await callback.answer("Произошла ошибка при обработке ставки")

async def play_slot_machine(callback: types.CallbackQuery, state: FSMContext):
    try:
        user_id = callback.from_user.id
        
        # Get the bet from storage
        data = await state.get_data()
        bet = data.get("slot_bet", 0)
        
        if bet <= 0:
            await callback.answer("Ставка не найдена, начните игру заново", show_alert=True)
            await state.clear()
            return
        
        # Define slot symbols
        symbols = ["🍒", "🍋", "🍊", "🍇", "🍎", "💎", "7️⃣"]
        weights = [20, 20, 15, 15, 10, 5, 2]  # Distribution weights
        
        # Spin the reels
        reel1 = random.choices(symbols, weights=weights, k=1)[0]
        reel2 = random.choices(symbols, weights=weights, k=1)[0]
        reel3 = random.choices(symbols, weights=weights, k=1)[0]
        
        # Animation (simulate spinning)
        message = await callback.message.edit_text(
            f"🎰 <b>Слот-машина</b>\n\n"
            f"Крутим барабаны...\n\n"
            f"[ ? ] [ ? ] [ ? ]"
        )
        
        # Simulate spinning animation
        await asyncio.sleep(0.5)
        await message.edit_text(
            f"🎰 <b>Слот-машина</b>\n\n"
            f"Крутим барабаны...\n\n"
            f"[ {reel1} ] [ ? ] [ ? ]"
        )
        
        await asyncio.sleep(0.5)
        await message.edit_text(
            f"🎰 <b>Слот-машина</b>\n\n"
            f"Крутим барабаны...\n\n"
            f"[ {reel1} ] [ {reel2} ] [ ? ]"
        )
        
        await asyncio.sleep(0.5)
        
        # Determine result
        result_text = ""
        stars_won = 0
        
        slot_result = f"[ {reel1} ] [ {reel2} ] [ {reel3} ]"
        
        # Check for wins
        if reel1 == reel2 == reel3:
            if reel1 == "7️⃣":  # Jackpot
                win_amount = bet * 50
                result_text = f"🎉 <b>ДЖЕКПОТ!!!</b> Получено {win_amount} звезд!"
            else:  # Three of a kind
                win_amount = bet * 10
                result_text = f"🎉 <b>Три в ряд!</b> Получено {win_amount} звезд!"
            stars_won = win_amount
        elif reel1 == reel2 or reel1 == reel3 or reel2 == reel3:
            win_amount = bet * 2
            result_text = f"🎉 <b>Два совпадения!</b> Получено {win_amount} звезд!"
            stars_won = win_amount
        else:
            result_text = f"😔 <b>Нет совпадений.</b> Потеряно {bet} звезд."
            stars_won = -bet
        
        # Update game stats
        update_game_stats(user_id, "slot_machine", stars_won)
        
        # Send final result
        await message.edit_text(
            f"🎰 <b>Результаты слот-машины</b>\n\n"
            f"{slot_result}\n\n"
            f"{result_text}",
            reply_markup=get_games_keyboard()
        )
        
        # Clear state
        await state.clear()
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in play_slot_machine: {e}")
        await state.clear()
        await callback.answer("Произошла ошибка при игре в слот-машину")

# Darts game handlers
async def show_darts_game(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🎯 <b>Дартс</b>\n\n"
        "Правила:\n"
        "- Вы бросаете дротик в мишень\n"
        "- Очки зависят от попадания:\n"
        "  • Центр (6): выигрыш x5\n"
        "  • Внутренний круг (5): выигрыш x3\n"
        "  • Средний круг (4): выигрыш x2\n"
        "  • Внешние круги (1-3): ставка проиграна\n\n"
        "Выберите сумму ставки:",
        reply_markup=get_bet_keyboard()
    )
    await callback.answer()

async def process_darts_bet(callback: types.CallbackQuery):
    try:
        bet = int(callback.data.split("_")[1])
        user_id = callback.from_user.id
        
        # Check if user has enough stars
        user_stats = get_user_stats(user_id)
        if not user_stats or user_stats[0] < bet:
            await callback.answer("У вас недостаточно звезд для этой ставки!", show_alert=True)
            return
        
        # Show play button
        buttons = [
            [InlineKeyboardButton(text="🎯 Метнуть дротик", callback_data="play_darts")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="game_darts")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            f"🎯 <b>Дартс</b>\n\n"
            f"Ваша ставка: {bet} звезд\n\n"
            f"Нажмите кнопку, чтобы метнуть дротик!",
            reply_markup=keyboard
        )
        
        # Save bet in storage
        await callback.bot.fsm_storage.set_data(
            bot=callback.bot,
            chat_id=callback.message.chat.id,
            user_id=user_id,
            data={"darts_bet": bet}
        )
        
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in process_darts_bet: {e}")
        await callback.answer("Произошла ошибка при обработке ставки")

async def play_darts_game(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id
        
        # Get the bet from storage
        data = await callback.bot.fsm_storage.get_data(
            bot=callback.bot,
            chat_id=callback.message.chat.id,
            user_id=user_id
        )
        bet = data.get("darts_bet", 0)
        
        if bet <= 0:
            await callback.answer("Ставка не найдена, начните игру заново", show_alert=True)
            return
        
        # Throw the dart
        dart = await callback.message.answer_dice(emoji="🎯")
        dart_value = dart.dice.value
        await asyncio.sleep(4)  # Wait for animation
        
        # Determine result
        result_text = ""
        stars_won = 0
        
        if dart_value == 6:  # Bullseye
            win_amount = bet * 5
            result_text = f"🎯 <b>Яблочко!</b> Получено {win_amount} звезд!"
            stars_won = win_amount
        elif dart_value == 5:  # Inner circle
            win_amount = bet * 3
            result_text = f"🎯 <b>Внутренний круг!</b> Получено {win_amount} звезд!"
            stars_won = win_amount
        elif dart_value == 4:  # Middle circle
            win_amount = bet * 2
            result_text = f"🎯 <b>Средний круг!</b> Получено {win_amount} звезд!"
            stars_won = win_amount
        else:  # Outer circles
            result_text = f"😔 <b>Внешние круги.</b> Потеряно {bet} звезд."
            stars_won = -bet
        
        # Update game stats
        update_game_stats(user_id, "darts", stars_won)
        
        # Send result
        await callback.message.answer(
            f"🎯 <b>Результаты игры в дартс</b>\n\n"
            f"Результат броска: {dart_value}/6\n\n"
            f"{result_text}",
            reply_markup=get_games_keyboard()
        )
        
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in play_darts_game: {e}")
        await callback.answer("Произошла ошибка при игре в дартс")
