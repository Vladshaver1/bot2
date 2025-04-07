from aiogram.fsm.state import State, StatesGroup

# Admin state machine
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
    waiting_for_ban_user_id = State()
    waiting_for_unban_user_id = State()

# Withdraw state machine
class WithdrawStates(StatesGroup):
    waiting_for_withdraw_amount = State()
    waiting_for_payment_info = State()

# Game state machine
class GameStates(StatesGroup):
    dice_game_bet = State()
    number_guess_bet = State()
    number_guess_playing = State()
    slot_machine_bet = State()
