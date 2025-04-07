from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Main menu keyboard
def get_main_menu_keyboard(user_id, bot_username):
    """Main menu keyboard with all options"""
    buttons = [
        [InlineKeyboardButton(
            text="📢 Поделиться ссылкой", 
            switch_inline_query=f"Присоединяйся к боту и зарабатывай звезды! https://t.me/{bot_username}?start={user_id}"
        )],
        [
            InlineKeyboardButton(text="📝 Список заданий", callback_data="tasks_list"),
            InlineKeyboardButton(text="💰 Мой баланс", callback_data="my_balance")
        ],
        [
            InlineKeyboardButton(text="🎮 Мини-игры", callback_data="mini_games"),
            InlineKeyboardButton(text="🏆 Топ игроков", callback_data="top_players")
        ],
        [
            InlineKeyboardButton(text="💸 Вывод звезд", callback_data="withdraw"),
            InlineKeyboardButton(text="🔗 Subgram", callback_data="subgram_integration")
        ],
        [
            InlineKeyboardButton(text="📱 Обязательные подписки", callback_data="subgram-op")
        ],
        [
            InlineKeyboardButton(text="❓ FAQ", callback_data="show_faq")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Back button
def get_back_button():
    """Simple back button to main menu"""
    buttons = [[InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Tasks list keyboard
def get_tasks_keyboard(tasks, user_id):
    """Generate keyboard with task buttons"""
    buttons = []
    
    for task_id, description, reward, completed in tasks:
        if not completed:
            buttons.append([InlineKeyboardButton(
                text=f"Выполнить задание {task_id}: {description[:20]}...", 
                callback_data=f"complete_task_{task_id}"
            )])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Mini-games menu
def get_games_keyboard():
    """Keyboard for mini-games selection"""
    buttons = [
        [
            InlineKeyboardButton(text="🎲 Кубики", callback_data="game_dice"),
            InlineKeyboardButton(text="🔢 Угадай число", callback_data="game_number")
        ],
        [
            InlineKeyboardButton(text="🎰 Слот-машина", callback_data="game_slot"),
            InlineKeyboardButton(text="🎯 Дартс", callback_data="game_darts")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Game bet keyboard
def get_bet_keyboard():
    """Keyboard for selecting bet amount"""
    buttons = [
        [
            InlineKeyboardButton(text="5 звезд", callback_data="bet_5"),
            InlineKeyboardButton(text="10 звезд", callback_data="bet_10"),
            InlineKeyboardButton(text="25 звезд", callback_data="bet_25")
        ],
        [
            InlineKeyboardButton(text="50 звезд", callback_data="bet_50"),
            InlineKeyboardButton(text="100 звезд", callback_data="bet_100")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="mini_games")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Admin menu keyboard
def get_admin_keyboard():
    """Keyboard for admin panel"""
    buttons = [
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="👤 Управление пользователями", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton(text="📝 Управление заданиями", callback_data="admin_tasks"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")
        ],
        [
            InlineKeyboardButton(text="💰 Запросы на вывод", callback_data="admin_withdrawals"),
            InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_mailing")
        ],
        [
            InlineKeyboardButton(text="📈 Статистика Subgram", callback_data="admin_subgram_stats"),
            InlineKeyboardButton(text="💹 Баланс Subgram", callback_data="admin_subgram_balance")
        ],
        [InlineKeyboardButton(text="🔙 Вернуться в основное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Admin tasks keyboard
def get_admin_tasks_keyboard():
    """Keyboard for task management"""
    buttons = [
        [
            InlineKeyboardButton(text="➕ Добавить задание", callback_data="add_task"),
            InlineKeyboardButton(text="📋 Список заданий", callback_data="list_all_tasks")
        ],
        [InlineKeyboardButton(text="🔙 Назад к админ-панели", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Admin users keyboard
def get_admin_users_keyboard():
    """Keyboard for user management"""
    buttons = [
        [
            InlineKeyboardButton(text="🔍 Найти пользователя", callback_data="search_user"),
            InlineKeyboardButton(text="🏆 Топ пользователей", callback_data="top_users")
        ],
        [
            InlineKeyboardButton(text="🚫 Забанить пользователя", callback_data="ban_user"),
            InlineKeyboardButton(text="✅ Разбанить пользователя", callback_data="unban_user")
        ],
        [InlineKeyboardButton(text="🔙 Назад к админ-панели", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Admin settings keyboard
def get_admin_settings_keyboard():
    """Keyboard for admin settings"""
    buttons = [
        [
            InlineKeyboardButton(text="🔄 Мин. рефералов", callback_data="set_min_referrals"),
            InlineKeyboardButton(text="📝 Мин. заданий", callback_data="set_min_tasks")
        ],
        [
            InlineKeyboardButton(text="💰 Бонус партнера", callback_data="set_partner_bonus"),
            InlineKeyboardButton(text="🔒 % воровства", callback_data="set_steal_percent")
        ],
        [
            InlineKeyboardButton(text="🔑 Заданий для кражи", callback_data="set_steal_unlock_tasks")
        ],
        [InlineKeyboardButton(text="🔙 Назад к админ-панели", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Withdraw keyboard
def get_withdraw_keyboard():
    """Keyboard for withdrawal screen"""
    buttons = [
        [
            InlineKeyboardButton(text="100 звезд", callback_data="withdraw_100"),
            InlineKeyboardButton(text="250 звезд", callback_data="withdraw_250"),
            InlineKeyboardButton(text="500 звезд", callback_data="withdraw_500")
        ],
        [
            InlineKeyboardButton(text="1000 звезд", callback_data="withdraw_1000"),
            InlineKeyboardButton(text="Другая сумма", callback_data="withdraw_custom")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Admin withdrawals keyboard
def get_admin_withdrawals_keyboard():
    """Keyboard for managing withdrawals"""
    buttons = [
        [
            InlineKeyboardButton(text="📋 Ожидающие", callback_data="withdrawals_pending"),
            InlineKeyboardButton(text="✅ Одобренные", callback_data="withdrawals_approved")
        ],
        [
            InlineKeyboardButton(text="❌ Отклоненные", callback_data="withdrawals_rejected"),
            InlineKeyboardButton(text="📊 Все запросы", callback_data="withdrawals_all")
        ],
        [InlineKeyboardButton(text="🔙 Назад к админ-панели", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Admin process withdrawal keyboard
def get_process_withdrawal_keyboard(withdrawal_id):
    """Keyboard for processing a specific withdrawal"""
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Одобрить", 
                callback_data=f"approve_withdrawal_{withdrawal_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отклонить", 
                callback_data=f"reject_withdrawal_{withdrawal_id}"
            )
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="withdrawals_pending")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Number guess game keyboard
def get_number_guess_keyboard():
    """Keyboard for number guessing game"""
    buttons = []
    for i in range(1, 11):
        button = InlineKeyboardButton(text=str(i), callback_data=f"guess_{i}")
        if i <= 5:
            if len(buttons) < 1:
                buttons.append([])
            buttons[0].append(button)
        else:
            if len(buttons) < 2:
                buttons.append([])
            buttons[1].append(button)
    
    buttons.append([InlineKeyboardButton(text="🔙 Отмена", callback_data="mini_games")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Admin task actions keyboard
def get_task_actions_keyboard(task_id, is_active):
    """Keyboard for task actions in admin panel"""
    status_text = "Деактивировать" if is_active else "Активировать"
    status_data = f"toggle_task_{task_id}"
    
    buttons = [
        [
            InlineKeyboardButton(text=status_text, callback_data=status_data),
            InlineKeyboardButton(text="Удалить", callback_data=f"delete_task_{task_id}")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="list_all_tasks")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
