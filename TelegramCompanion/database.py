import sqlite3
import datetime
import logging
from config import DB_NAME, DEFAULT_MIN_REFERRALS, DEFAULT_MIN_TASKS, DEFAULT_PARTNER_BONUS, DEFAULT_STEAL_PERCENT, DEFAULT_STEAL_UNLOCK_TASKS

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        
    def get_app(self):
        """Get Flask app for context management"""
        import app as flask_app
        return flask_app
    
    def create_tables(self):
        """Create database tables if they don't exist"""
        try:
            # Subgram exchanges table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS subgram_exchanges (
                exchange_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                stars_amount INTEGER,
                subgram_amount REAL,
                exchange_date TEXT,
                status TEXT DEFAULT 'completed',
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )''')
            
            # Subscription rewards table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscription_rewards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                channel_id TEXT,
                channel_name TEXT,
                stars_amount INTEGER,
                reward_date TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )''')
            
            # Required Channels table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS required_channels (
                channel_id TEXT PRIMARY KEY,
                channel_name TEXT NOT NULL,
                stars_reward INTEGER DEFAULT 10,
                added_date TEXT
            )''')
            
            # Users table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                referral_id INTEGER,
                stars INTEGER DEFAULT 0,
                completed_tasks INTEGER DEFAULT 0,
                referrals_count INTEGER DEFAULT 0,
                last_activity TEXT,
                is_banned INTEGER DEFAULT 0,
                reg_date TEXT,
                daily_games INTEGER DEFAULT 0,
                last_game_date TEXT
            )''')
            
            # Tasks table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT,
                reward INTEGER,
                is_active INTEGER DEFAULT 1
            )''')
            
            # User tasks table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_tasks (
                user_id INTEGER,
                task_id INTEGER,
                completed_date TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(task_id) REFERENCES tasks(task_id),
                PRIMARY KEY(user_id, task_id)
            )''')
            
            # Withdrawals table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdrawals (
                withdrawal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                status TEXT DEFAULT 'pending',
                request_date TEXT,
                process_date TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )''')
            
            # Admin settings table
            self.cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS admin_settings (
                min_referrals INTEGER DEFAULT {DEFAULT_MIN_REFERRALS},
                min_tasks INTEGER DEFAULT {DEFAULT_MIN_TASKS},
                partner_bonus INTEGER DEFAULT {DEFAULT_PARTNER_BONUS},
                steal_percent INTEGER DEFAULT {DEFAULT_STEAL_PERCENT},
                steal_unlock_tasks INTEGER DEFAULT {DEFAULT_STEAL_UNLOCK_TASKS}
            )''')
            
            # Add default admin settings if table is empty
            self.cursor.execute('SELECT COUNT(*) FROM admin_settings')
            if self.cursor.fetchone()[0] == 0:
                self.cursor.execute('INSERT INTO admin_settings DEFAULT VALUES')
            
            # Не добавляем тестовые задания - используем только задания от спонсоров
            
            self.conn.commit()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
    
    def add_user(self, user_id, username, full_name, referral_id=None):
        """Add a new user to the database"""
        try:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute('''
            INSERT INTO users (user_id, username, full_name, referral_id, reg_date, last_activity)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, username, full_name, referral_id, now, now))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False
    
    def get_user(self, user_id):
        """Get user data by user_id"""
        try:
            self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def update_user_activity(self, user_id):
        """Update user's last activity timestamp"""
        try:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                'UPDATE users SET last_activity = ? WHERE user_id = ?', 
                (now, user_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating user activity: {e}")
            return False
    
    def increase_referral_count(self, referral_id):
        """Increase referral count for a user and add bonus stars with protection against fraud"""
        try:
            # Проверка на максимальное число рефералов в день (защита от накрутки)
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            self.cursor.execute(
                "SELECT COUNT(*) FROM users WHERE referral_id = ? AND reg_date LIKE ?",
                (referral_id, f"{today}%")
            )
            today_referrals = self.cursor.fetchone()[0]
            
            if today_referrals >= 10:  # Максимум 10 рефералов в день
                logger.warning(f"User {referral_id} has reached daily referral limit")
                return False
            
            # Обновляем счетчик рефералов
            self.cursor.execute('UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?', (referral_id,))
            
            # Устанавливаем фиксированную награду за реферала - 0.5 звезды
            partner_bonus = 0.5
            self.cursor.execute('UPDATE users SET stars = stars + ? WHERE user_id = ?', (partner_bonus, referral_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error increasing referral count: {e}")
            return False
    
    def get_user_stats(self, user_id):
        """Get user statistics"""
        try:
            self.cursor.execute(
                'SELECT stars, completed_tasks, referrals_count FROM users WHERE user_id = ?', 
                (user_id,)
            )
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return None
    
    def get_admin_settings(self):
        """Get admin settings"""
        try:
            self.cursor.execute('SELECT * FROM admin_settings LIMIT 1')
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting admin settings: {e}")
            return None
    
    def get_active_tasks(self):
        """Get all active tasks"""
        try:
            self.cursor.execute('SELECT task_id, description, reward FROM tasks WHERE is_active = 1')
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting active tasks: {e}")
            return []
    
    def check_task_completed(self, user_id, task_id):
        """Check if user has completed a task"""
        try:
            self.cursor.execute(
                'SELECT 1 FROM user_tasks WHERE user_id = ? AND task_id = ?', 
                (user_id, task_id)
            )
            return self.cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking task completion: {e}")
            return False
    
    def complete_task(self, user_id, task_id):
        """Mark a task as completed and update user stats"""
        try:
            # Check if task is already completed
            if self.check_task_completed(user_id, task_id):
                return False
            
            # Задаем фиксированную награду в 0.25 звезд за задание вместо получения из БД
            reward = 0.25
            
            # Add task completion record
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                'INSERT INTO user_tasks (user_id, task_id, completed_date) VALUES (?, ?, ?)',
                (user_id, task_id, now)
            )
            
            # Update user stats
            self.cursor.execute(
                'UPDATE users SET stars = stars + ?, completed_tasks = completed_tasks + 1 WHERE user_id = ?',
                (reward, user_id)
            )
            
            self.conn.commit()
            return reward
        except Exception as e:
            logger.error(f"Error completing task: {e}")
            return False
    
    def add_task(self, description, reward):
        """Add a new task"""
        try:
            self.cursor.execute(
                'INSERT INTO tasks (description, reward, is_active) VALUES (?, ?, 1)',
                (description, reward)
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding task: {e}")
            return None
    
    def toggle_task_status(self, task_id):
        """Toggle task active status"""
        try:
            self.cursor.execute(
                'UPDATE tasks SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE task_id = ?',
                (task_id,)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error toggling task status: {e}")
            return False
    
    def request_withdrawal(self, user_id, amount):
        """Create a withdrawal request"""
        try:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                'INSERT INTO withdrawals (user_id, amount, status, request_date) VALUES (?, ?, "pending", ?)',
                (user_id, amount, now)
            )
            
            # Deduct stars from user
            self.cursor.execute(
                'UPDATE users SET stars = stars - ? WHERE user_id = ?',
                (amount, user_id)
            )
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error requesting withdrawal: {e}")
            return False
    
    def get_pending_withdrawals(self):
        """Get all pending withdrawal requests"""
        try:
            self.cursor.execute('''
            SELECT w.withdrawal_id, w.user_id, u.username, w.amount, w.request_date 
            FROM withdrawals w 
            JOIN users u ON w.user_id = u.user_id 
            WHERE w.status = "pending" 
            ORDER BY w.request_date ASC
            ''')
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting pending withdrawals: {e}")
            return []
    
    def process_withdrawal(self, withdrawal_id, status):
        """Process a withdrawal request"""
        try:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                'UPDATE withdrawals SET status = ?, process_date = ? WHERE withdrawal_id = ?',
                (status, now, withdrawal_id)
            )
            
            # If rejected, return stars to user
            if status == 'rejected':
                self.cursor.execute('SELECT user_id, amount FROM withdrawals WHERE withdrawal_id = ?', (withdrawal_id,))
                user_id, amount = self.cursor.fetchone()
                self.cursor.execute(
                    'UPDATE users SET stars = stars + ? WHERE user_id = ?',
                    (amount, user_id)
                )
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error processing withdrawal: {e}")
            return False
    
    def get_top_users(self, limit=10):
        """Get top users by stars"""
        try:
            self.cursor.execute('''
            SELECT user_id, username, full_name, stars, referrals_count, completed_tasks
            FROM users 
            WHERE is_banned = 0
            ORDER BY stars DESC 
            LIMIT ?
            ''', (limit,))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting top users: {e}")
            return []
    
    def update_admin_settings(self, min_referrals=None, min_tasks=None, partner_bonus=None, steal_percent=None, steal_unlock_tasks=None):
        """Update admin settings"""
        try:
            update_fields = []
            params = []
            
            if min_referrals is not None:
                update_fields.append("min_referrals = ?")
                params.append(min_referrals)
            
            if min_tasks is not None:
                update_fields.append("min_tasks = ?")
                params.append(min_tasks)
            
            if partner_bonus is not None:
                update_fields.append("partner_bonus = ?")
                params.append(partner_bonus)
            
            if steal_percent is not None:
                update_fields.append("steal_percent = ?")
                params.append(steal_percent)
            
            if steal_unlock_tasks is not None:
                update_fields.append("steal_unlock_tasks = ?")
                params.append(steal_unlock_tasks)
            
            if update_fields:
                query = f"UPDATE admin_settings SET {', '.join(update_fields)}"
                self.cursor.execute(query, params)
                self.conn.commit()
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error updating admin settings: {e}")
            return False
    
    def update_user_stars(self, user_id, stars_change):
        """Update user stars (add or subtract)"""
        try:
            self.cursor.execute(
                'UPDATE users SET stars = stars + ? WHERE user_id = ?',
                (stars_change, user_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating user stars: {e}")
            return False
            
    def reset_all_users_stars(self):
        """Reset stars to zero for all users"""
        try:
            self.cursor.execute('UPDATE users SET stars = 0')
            self.conn.commit()
            return True, "Звезды всех пользователей обнулены."
        except Exception as e:
            logger.error(f"Error resetting all users stars: {e}")
            return False, f"Ошибка при обнулении звезд: {str(e)}"

    def ban_user(self, user_id, ban_status=1):
        """Ban or unban a user"""
        try:
            self.cursor.execute(
                'UPDATE users SET is_banned = ? WHERE user_id = ?',
                (ban_status, user_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error changing user ban status: {e}")
            return False
            
    def delete_user(self, user_id):
        """Delete a user completely from the database"""
        try:
            # Start a transaction
            self.conn.execute('BEGIN TRANSACTION')
            
            # Delete from user_tasks table
            self.cursor.execute('DELETE FROM user_tasks WHERE user_id = ?', (user_id,))
            
            # Delete from withdrawals table
            self.cursor.execute('DELETE FROM withdrawals WHERE user_id = ?', (user_id,))
            
            # Delete from game_stats table if exists
            try:
                self.cursor.execute('DELETE FROM game_stats WHERE user_id = ?', (user_id,))
            except sqlite3.OperationalError:
                # Table might not exist, ignore
                pass
            
            # Delete from subscription_rewards table
            self.cursor.execute('DELETE FROM subscription_rewards WHERE user_id = ?', (user_id,))
            
            # Delete from subgram_exchanges table
            self.cursor.execute('DELETE FROM subgram_exchanges WHERE user_id = ?', (user_id,))
            
            # Delete from subgram_offers table if exists
            try:
                self.cursor.execute('DELETE FROM subgram_offers WHERE user_id = ?', (user_id,))
            except sqlite3.OperationalError:
                # Table might not exist in SQLite, ignore
                pass
            
            # Finally delete from users table
            self.cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
            
            # Commit the transaction
            self.conn.commit()
            
            # Синхронизация удаления с PostgreSQL базой данных (web dashboard)
            try:
                app = self.get_app()
                # Создаем контекст приложения Flask для работы с моделями SQLAlchemy
                with app.app.app_context():
                    user = app.User.query.filter_by(user_id=user_id).first()
                    if user:
                        # Удаляем связанные записи
                        app.UserTask.query.filter_by(user_id=user_id).delete()
                        app.Withdrawal.query.filter_by(user_id=user_id).delete()
                        app.GameStats.query.filter_by(user_id=user_id).delete()
                        app.SubgramExchange.query.filter_by(user_id=user_id).delete()
                        app.SubscriptionReward.query.filter_by(user_id=user_id).delete()
                        app.SubgramOffer.query.filter_by(user_id=user_id).delete()
                        
                        # Удаляем самого пользователя
                        app.db.session.delete(user)
                        app.db.session.commit()
                        logger.info(f"User {user_id} successfully deleted from PostgreSQL database")
            except Exception as e:
                logger.error(f"Error deleting user from PostgreSQL: {e}")
                # Продолжаем выполнение, так как удаление из SQLite уже завершено успешно
            
            logger.info(f"User {user_id} successfully deleted from database")
            return True
        except Exception as e:
            # Rollback in case of error
            self.conn.rollback()
            logger.error(f"Error deleting user: {e}")
            return False
    
    def get_user_game_stats(self, user_id):
        """Get user's daily game statistics"""
        try:
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            self.cursor.execute(
                '''SELECT daily_games, last_game_date FROM users WHERE user_id = ?''',
                (user_id,)
            )
            result = self.cursor.fetchone()
            
            if result:
                daily_games, last_game_date = result
                
                # Reset daily counter if it's a new day
                if last_game_date and not last_game_date.startswith(today):
                    self.reset_daily_game_counter(user_id)
                    return 0
                
                return daily_games
            
            return 0
        except Exception as e:
            logger.error(f"Error getting user game stats: {e}")
            return 0
    
    def reset_daily_game_counter(self, user_id):
        """Reset the daily game counter for a user"""
        try:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                'UPDATE users SET daily_games = 0, last_game_date = ? WHERE user_id = ?',
                (now, user_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error resetting game counter: {e}")
            return False
    
    def increment_game_counter(self, user_id):
        """Increment the daily game counter for a user"""
        try:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                'UPDATE users SET daily_games = daily_games + 1, last_game_date = ? WHERE user_id = ?',
                (now, user_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error incrementing game counter: {e}")
            return False

    def log_subgram_exchange(self, user_id, stars_amount, subgram_amount, status='completed'):
        """Log a Subgram exchange"""
        try:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                '''INSERT INTO subgram_exchanges 
                   (user_id, stars_amount, subgram_amount, exchange_date, status) 
                   VALUES (?, ?, ?, ?, ?)''',
                (user_id, stars_amount, subgram_amount, now, status)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error logging Subgram exchange: {e}")
            return False
            
    def get_subgram_exchanges(self, limit=None):
        """Get Subgram exchanges"""
        try:
            query = '''
            SELECT e.exchange_id, e.user_id, u.username, e.stars_amount, 
                   e.subgram_amount, e.exchange_date, e.status
            FROM subgram_exchanges e
            JOIN users u ON e.user_id = u.user_id
            ORDER BY e.exchange_date DESC
            '''
            
            if limit:
                query += ' LIMIT ?'
                self.cursor.execute(query, (limit,))
            else:
                self.cursor.execute(query)
                
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting Subgram exchanges: {e}")
            return []
            
    def get_subgram_stats(self):
        """Get Subgram exchange statistics"""
        try:
            stats = {}
            
            # Get total exchanges count
            self.cursor.execute('SELECT COUNT(*) FROM subgram_exchanges')
            stats['exchanges_count'] = self.cursor.fetchone()[0]
            
            # Get unique users count
            self.cursor.execute('SELECT COUNT(DISTINCT user_id) FROM subgram_exchanges')
            stats['unique_users'] = self.cursor.fetchone()[0]
            
            # Get total stars exchanged
            self.cursor.execute('SELECT SUM(stars_amount) FROM subgram_exchanges')
            stats['total_stars'] = self.cursor.fetchone()[0] or 0
            
            # Get total Subgram amount
            self.cursor.execute('SELECT SUM(subgram_amount) FROM subgram_exchanges')
            stats['total_rubles'] = self.cursor.fetchone()[0] or 0
            
            return stats
        except Exception as e:
            logger.error(f"Error getting Subgram stats: {e}")
            return {
                'exchanges_count': 0,
                'unique_users': 0,
                'total_stars': 0,
                'total_rubles': 0
            }
    
    def steal_stars(self, thief_id, victim_id, amount):
        """Steal stars from one user and give to another"""
        try:
            # Check if victim has enough stars
            self.cursor.execute('SELECT stars FROM users WHERE user_id = ?', (victim_id,))
            victim_stars = self.cursor.fetchone()[0]
            
            if victim_stars < amount:
                amount = victim_stars  # Only steal what's available
            
            if amount <= 0:
                return 0
            
            # Execute the theft
            self.cursor.execute('UPDATE users SET stars = stars - ? WHERE user_id = ?', (amount, victim_id))
            self.cursor.execute('UPDATE users SET stars = stars + ? WHERE user_id = ?', (amount, thief_id))
            
            self.conn.commit()
            return amount
        except Exception as e:
            logger.error(f"Error stealing stars: {e}")
            return 0
    
    def log_subscription_reward(self, user_id, channel_id, channel_name, stars_amount):
        """Log a reward for channel subscription"""
        try:
            # Check if user already received reward for this channel
            self.cursor.execute(
                "SELECT 1 FROM subscription_rewards WHERE user_id = ? AND channel_id = ?",
                (user_id, channel_id)
            )
            
            if self.cursor.fetchone():
                # Already rewarded
                return False
            
            # Record the reward
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                """
                INSERT INTO subscription_rewards 
                (user_id, channel_id, channel_name, stars_amount, reward_date)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, channel_id, channel_name, stars_amount, now)
            )
            
            # Update user stars
            self.cursor.execute(
                "UPDATE users SET stars = stars + ? WHERE user_id = ?",
                (stars_amount, user_id)
            )
            
            self.conn.commit()
            self.update_user_activity(user_id)
            return True
        except Exception as e:
            logger.error(f"Error logging subscription reward: {e}")
            return False
    
    def get_user_subscription_rewards(self, user_id):
        """Get subscription rewards for a user"""
        try:
            self.cursor.execute(
                """
                SELECT channel_id, channel_name, stars_amount, reward_date 
                FROM subscription_rewards 
                WHERE user_id = ?
                ORDER BY reward_date DESC
                """,
                (user_id,)
            )
            
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting user subscription rewards: {e}")
            return []
    
    def get_subscription_stats(self):
        """Get subscription reward statistics"""
        try:
            # Get total subscriptions
            self.cursor.execute("SELECT COUNT(*) FROM subscription_rewards")
            total_subscriptions = self.cursor.fetchone()[0] or 0
            
            # Get total stars rewarded
            self.cursor.execute("SELECT SUM(stars_amount) FROM subscription_rewards")
            total_stars = self.cursor.fetchone()[0] or 0
            
            # Get subscriptions per channel
            self.cursor.execute(
                """
                SELECT channel_id, channel_name, COUNT(*) as count 
                FROM subscription_rewards 
                GROUP BY channel_id
                ORDER BY count DESC
                """
            )
            
            channels = self.cursor.fetchall()
            
            return {
                'total_subscriptions': total_subscriptions,
                'total_stars_rewarded': total_stars,
                'channels': channels
            }
        except Exception as e:
            logger.error(f"Error getting subscription stats: {e}")
            return {'total_subscriptions': 0, 'total_stars_rewarded': 0, 'channels': []}
    
    def get_required_channels(self):
        """Get list of required subscription channels"""
        try:
            self.cursor.execute('''
            SELECT channel_id, channel_name, stars_reward, added_date 
            FROM required_channels
            ORDER BY added_date DESC
            ''')
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting required channels: {e}")
            return []
    
    def add_required_channel(self, channel_id, channel_name, stars_reward=10):
        """Add a new required subscription channel"""
        try:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute('''
            INSERT INTO required_channels (channel_id, channel_name, stars_reward, added_date)
            VALUES (?, ?, ?, ?)
            ''', (channel_id, channel_name, stars_reward, now))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding required channel: {e}")
            return False
    
    def remove_required_channel(self, channel_id):
        """Remove a channel from required subscriptions"""
        try:
            self.cursor.execute('DELETE FROM required_channels WHERE channel_id = ?', (channel_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error removing required channel: {e}")
            return False
    
    def update_channel_reward(self, channel_id, stars_reward):
        """Update stars reward for a channel"""
        try:
            self.cursor.execute(
                'UPDATE required_channels SET stars_reward = ? WHERE channel_id = ?',
                (stars_reward, channel_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating channel reward: {e}")
            return False
            
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
