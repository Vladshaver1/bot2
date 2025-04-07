import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot settings
API_TOKEN = os.getenv('API_TOKEN')
if not API_TOKEN:
    raise ValueError("API_TOKEN environment variable is not set")

# Subgram API settings
SUBGRAM_API_KEY = os.getenv('SUBGRAM_API_KEY')
if not SUBGRAM_API_KEY:
    raise ValueError("SUBGRAM_API_KEY environment variable is not set")

# Admin settings
ADMIN_ID = 7919687991

# Database settings
DB_NAME = 'referral_bot.db'

# Default admin settings
DEFAULT_MIN_REFERRALS = 35
DEFAULT_MIN_TASKS = 40
DEFAULT_PARTNER_BONUS = 0.5  # Изменено с 10 на 0.5
DEFAULT_STEAL_PERCENT = 1
DEFAULT_STEAL_UNLOCK_TASKS = 25

# Защита от накрутки рефералов
REFERRAL_PROTECTION = True  # Включить защиту от накрутки рефералов
REFERRAL_MIN_ACTIVITY = 2  # Минимальное количество действий для учета реферала
REFERRAL_MAX_PER_DAY = 10  # Максимальное количество рефералов в день от одного пользователя

# Game settings
GAME_DAILY_LIMIT = 3
DICE_REWARD = {
    1: 1,  # 1 star
    2: 2,  # 2 stars
    3: 3,  # 3 stars
    4: 4,  # 4 stars
    5: 5,  # 5 stars
    6: 10  # 10 stars
}
SLOTS_REWARD = {
    '🍒': 3,    # 3 stars
    '🍋': 5,    # 5 stars
    '7️⃣': 10,   # 10 stars
    '💎': 20    # 20 stars
}
