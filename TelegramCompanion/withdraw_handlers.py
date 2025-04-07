import logging
from aiogram import types, Bot, F, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from models import WithdrawStates
from database import get_user_stats, get_admin_settings, create_withdrawal_request
from keyboards import get_withdraw_keyboard, get_back_button

logger = logging.getLogger(__name__)

# Register withdraw handlers
def register_handlers(dp: Dispatcher, bot: Bot):
    # Withdraw menu
    dp.callback_query.register(show_withdraw_menu, F.data == "withdraw")
    
    # Process withdraw amounts
    dp.callback_query.register(process_withdraw_amount, F.data.startswith("withdraw_"))
    
    # Custom withdraw amount handling
    dp.message.register(process_custom_withdraw, WithdrawStates.waiting_for_withdraw_amount)
    
    # Payment info handling
    dp.message.register(process_payment_info, WithdrawStates.waiting_for_payment_info)
    
    logger.info("Withdraw handlers registered")

# Show withdraw menu
async def show_withdraw_menu(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id
        
        # Get user stats and settings
        user_stats = get_user_stats(user_id)
        settings = get_admin_settings()
        
        if not user_stats or not settings:
            await callback.answer("❌ Произошла ошибка при получении данных", show_alert=True)
            return
        
        stars, completed_tasks, referrals_count = user_stats
        min_referrals, min_tasks, _, _, _ = settings
        
        # Check if user meets the requirements
        if completed_tasks < min_tasks or referrals_count < min_referrals:
            await callback.answer(
                f"⚠️ Для вывода необходимо:\n"
                f"- Пригласить {min_referrals} друзей (у вас {referrals_count})\n"
                f"- Выполнить {min_tasks} заданий (у вас {completed_tasks})",
                show_alert=True
            )
            return
        
        withdraw_text = (
            f"💸 <b>Вывод звезд</b>\n\n"
            f"Ваш баланс: {stars} звезд\n\n"
            f"Выберите сумму для вывода или введите другую сумму:"
        )
        
        await callback.message.edit_text(
            withdraw_text,
            reply_markup=get_withdraw_keyboard()
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in show_withdraw_menu: {e}")
        await callback.answer("Произошла ошибка при открытии меню вывода", show_alert=True)

# Process withdraw amount selection
async def process_withdraw_amount(callback: types.CallbackQuery, state: FSMContext):
    try:
        user_id = callback.from_user.id
        
        # Handle custom amount option
        if callback.data == "withdraw_custom":
            await state.set_state(WithdrawStates.waiting_for_withdraw_amount)
            
            buttons = [[InlineKeyboardButton(text="🔙 Назад", callback_data="withdraw")]]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            await callback.message.edit_text(
                "💸 <b>Вывод звезд</b>\n\n"
                "Введите сумму для вывода (целое число):",
                reply_markup=keyboard
            )
            await callback.answer()
            return
        
        # Get selected amount
        amount = int(callback.data.split("_")[1])
        
        # Check if user has enough stars
        user_stats = get_user_stats(user_id)
        if not user_stats or user_stats[0] < amount:
            await callback.answer("❌ У вас недостаточно звезд для этого вывода", show_alert=True)
            return
        
        # Save withdrawal amount
        await state.update_data(withdraw_amount=amount)
        await state.set_state(WithdrawStates.waiting_for_payment_info)
        
        buttons = [[InlineKeyboardButton(text="🔙 Отмена", callback_data="withdraw")]]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            f"💸 <b>Вывод {amount} звезд</b>\n\n"
            f"Введите информацию для получения выплаты (например, номер кошелька или карты):",
            reply_markup=keyboard
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in process_withdraw_amount: {e}")
        await callback.answer("Произошла ошибка при обработке суммы вывода", show_alert=True)

# Process custom withdraw amount
async def process_custom_withdraw(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        
        # Parse amount
        try:
            amount = int(message.text.strip())
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except ValueError:
            await message.answer(
                "❌ Введите корректную сумму (положительное целое число)",
                reply_markup=get_back_button()
            )
            return
        
        # Check if user has enough stars
        user_stats = get_user_stats(user_id)
        if not user_stats or user_stats[0] < amount:
            await message.answer(
                "❌ У вас недостаточно звезд для этого вывода",
                reply_markup=get_back_button()
            )
            return
        
        # Save withdrawal amount
        await state.update_data(withdraw_amount=amount)
        await state.set_state(WithdrawStates.waiting_for_payment_info)
        
        buttons = [[InlineKeyboardButton(text="🔙 Отмена", callback_data="withdraw")]]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await message.answer(
            f"💸 <b>Вывод {amount} звезд</b>\n\n"
            f"Введите информацию для получения выплаты (например, номер кошелька или карты):",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error in process_custom_withdraw: {e}")
        await message.answer(
            "❌ Произошла ошибка при обработке суммы вывода",
            reply_markup=get_back_button()
        )
        await state.clear()

# Process payment information
async def process_payment_info(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        payment_info = message.text.strip()
        
        if not payment_info:
            await message.answer(
                "❌ Информация для выплаты не может быть пустой. Попробуйте еще раз:"
            )
            return
        
        # Get withdraw amount from state
        data = await state.get_data()
        amount = data.get("withdraw_amount", 0)
        
        if amount <= 0:
            await message.answer(
                "❌ Некорректная сумма вывода. Начните заново.",
                reply_markup=get_back_button()
            )
            await state.clear()
            return
        
        # Create withdrawal request
        success, result_message = create_withdrawal_request(user_id, amount)
        
        if success:
            await message.answer(
                f"✅ <b>Заявка на вывод создана!</b>\n\n"
                f"Сумма: {amount} звезд\n"
                f"Информация для выплаты: {payment_info}\n\n"
                f"Ваша заявка будет обработана администратором в ближайшее время.",
                reply_markup=get_back_button()
            )
        else:
            await message.answer(
                f"❌ {result_message}",
                reply_markup=get_back_button()
            )
        
        await state.clear()
    except Exception as e:
        logger.error(f"Error in process_payment_info: {e}")
        await message.answer(
            "❌ Произошла ошибка при создании заявки на вывод",
            reply_markup=get_back_button()
        )
        await state.clear()
