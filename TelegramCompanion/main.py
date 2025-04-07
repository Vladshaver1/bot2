import asyncio
import logging
import os
import signal
import sqlite3
import sys
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode

# Global shutdown flag
should_exit = False

import bot_handlers
import admin_handlers
import subgram_handlers
from utils import setup_logging
from config import API_TOKEN, DB_NAME

# For the web application
from app import app, db, User, Task, UserTask, Withdrawal, AdminSettings, GameStats, SubgramExchange, SubscriptionReward, RequiredChannel

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Register routers
dp.include_router(bot_handlers.router)
dp.include_router(admin_handlers.router)
# Register Subgram handlers
subgram_handlers.register_handlers(dp)

def sync_sqlite_to_postgres():
    """Synchronize data from SQLite database to PostgreSQL"""
    try:
        logger.info("Starting database synchronization from SQLite to PostgreSQL...")
        
        # Connect to SQLite database
        sqlite_conn = sqlite3.connect(DB_NAME)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        
        with app.app_context():
            # 1. Sync users
            sqlite_cursor.execute('''
            SELECT user_id, username, full_name, referral_id, stars, 
                   completed_tasks, referrals_count, last_activity, 
                   is_banned, reg_date
            FROM users
            ''')
            users = sqlite_cursor.fetchall()
            
            # Логирование для отладки
            logger.info(f"Found {len(users)} users in SQLite database")
            
            for user in users:
                try:
                    # Check if user exists in PostgreSQL
                    pg_user = User.query.filter_by(user_id=user['user_id']).first()
                    
                    if pg_user:
                        # Update existing user
                        pg_user.username = user['username']
                        pg_user.full_name = user['full_name']
                        pg_user.referral_id = user['referral_id']
                        pg_user.stars = user['stars']
                        pg_user.completed_tasks = user['completed_tasks']
                        pg_user.referrals_count = user['referrals_count']
                        
                        if user['last_activity']:
                            try:
                                pg_user.last_activity = datetime.strptime(user['last_activity'], '%Y-%m-%d %H:%M:%S')
                            except Exception as e:
                                logger.warning(f"Error parsing last_activity for user {user['user_id']}: {e}")
                                pg_user.last_activity = datetime.now()
                        
                        pg_user.is_banned = bool(user['is_banned'])
                        
                        if user['reg_date']:
                            try:
                                pg_user.reg_date = datetime.strptime(user['reg_date'], '%Y-%m-%d %H:%M:%S')
                            except Exception as e:
                                logger.warning(f"Error parsing reg_date for user {user['user_id']}: {e}")
                                pg_user.reg_date = datetime.now()
                        
                        logger.debug(f"Updated existing user {user['user_id']} in PostgreSQL")
                    else:
                        # Create new user
                        new_user = User(
                            user_id=user['user_id'],
                            username=user['username'],
                            full_name=user['full_name'],
                            referral_id=user['referral_id'],
                            stars=user['stars'],
                            completed_tasks=user['completed_tasks'],
                            referrals_count=user['referrals_count'],
                            is_banned=bool(user['is_banned'])
                        )
                        
                        if user['last_activity']:
                            try:
                                new_user.last_activity = datetime.strptime(user['last_activity'], '%Y-%m-%d %H:%M:%S')
                            except Exception as e:
                                logger.warning(f"Error parsing last_activity for new user {user['user_id']}: {e}")
                                new_user.last_activity = datetime.now()
                        
                        if user['reg_date']:
                            try:
                                new_user.reg_date = datetime.strptime(user['reg_date'], '%Y-%m-%d %H:%M:%S')
                            except Exception as e:
                                logger.warning(f"Error parsing reg_date for new user {user['user_id']}: {e}")
                                new_user.reg_date = datetime.now()
                        
                        db.session.add(new_user)
                        # Немедленная фиксация изменения
                        db.session.flush()
                        logger.info(f"Added new user {user['user_id']} to PostgreSQL")
                except Exception as e:
                    logger.error(f"Error syncing user {user['user_id']} to PostgreSQL: {e}")
                    # Continue with next user
            
            # 2. Sync tasks
            sqlite_cursor.execute('SELECT task_id, description, reward, is_active FROM tasks')
            tasks = sqlite_cursor.fetchall()
            
            for task in tasks:
                # Check if task exists in PostgreSQL
                pg_task = Task.query.filter_by(id=task['task_id']).first()
                
                if pg_task:
                    # Update existing task
                    pg_task.description = task['description']
                    pg_task.reward = task['reward']
                    pg_task.is_active = bool(task['is_active'])
                else:
                    # Create new task
                    new_task = Task(
                        id=task['task_id'],
                        description=task['description'],
                        reward=task['reward'],
                        is_active=bool(task['is_active'])
                    )
                    db.session.add(new_task)
            
            # 3. Sync user tasks
            sqlite_cursor.execute('''
            SELECT user_id, task_id, completed_date FROM user_tasks
            ''')
            user_tasks = sqlite_cursor.fetchall()
            
            for user_task in user_tasks:
                # Check if user task exists in PostgreSQL
                pg_user_task = UserTask.query.filter_by(
                    user_id=user_task['user_id'], 
                    task_id=user_task['task_id']
                ).first()
                
                if not pg_user_task:
                    # Create new user task
                    new_user_task = UserTask(
                        user_id=user_task['user_id'],
                        task_id=user_task['task_id']
                    )
                    
                    if user_task['completed_date']:
                        try:
                            new_user_task.completed_date = datetime.strptime(user_task['completed_date'], '%Y-%m-%d %H:%M:%S')
                        except:
                            new_user_task.completed_date = datetime.now()
                    
                    db.session.add(new_user_task)
            
            # 4. Sync withdrawals
            sqlite_cursor.execute('''
            SELECT withdrawal_id, user_id, amount, status, request_date, process_date 
            FROM withdrawals
            ''')
            withdrawals = sqlite_cursor.fetchall()
            
            for withdrawal in withdrawals:
                # Check if withdrawal exists in PostgreSQL
                pg_withdrawal = Withdrawal.query.filter_by(id=withdrawal['withdrawal_id']).first()
                
                if pg_withdrawal:
                    # Update existing withdrawal
                    pg_withdrawal.user_id = withdrawal['user_id']
                    pg_withdrawal.amount = withdrawal['amount']
                    pg_withdrawal.status = withdrawal['status']
                    
                    if withdrawal['request_date']:
                        try:
                            pg_withdrawal.request_date = datetime.strptime(withdrawal['request_date'], '%Y-%m-%d %H:%M:%S')
                        except:
                            pg_withdrawal.request_date = datetime.now()
                    
                    if withdrawal['process_date']:
                        try:
                            pg_withdrawal.process_date = datetime.strptime(withdrawal['process_date'], '%Y-%m-%d %H:%M:%S')
                        except:
                            pg_withdrawal.process_date = None
                else:
                    # Create new withdrawal
                    new_withdrawal = Withdrawal(
                        id=withdrawal['withdrawal_id'],
                        user_id=withdrawal['user_id'],
                        amount=withdrawal['amount'],
                        status=withdrawal['status']
                    )
                    
                    if withdrawal['request_date']:
                        try:
                            new_withdrawal.request_date = datetime.strptime(withdrawal['request_date'], '%Y-%m-%d %H:%M:%S')
                        except:
                            new_withdrawal.request_date = datetime.now()
                    
                    if withdrawal['process_date']:
                        try:
                            new_withdrawal.process_date = datetime.strptime(withdrawal['process_date'], '%Y-%m-%d %H:%M:%S')
                        except:
                            new_withdrawal.process_date = None
                    
                    db.session.add(new_withdrawal)
            
            # 5. Sync admin settings
            sqlite_cursor.execute('''
            SELECT min_referrals, min_tasks, partner_bonus, steal_percent, steal_unlock_tasks 
            FROM admin_settings LIMIT 1
            ''')
            settings = sqlite_cursor.fetchone()
            
            if settings:
                pg_settings = AdminSettings.query.first()
                
                if pg_settings:
                    # Update existing settings
                    pg_settings.min_referrals = settings['min_referrals']
                    pg_settings.min_tasks = settings['min_tasks']
                    pg_settings.partner_bonus = settings['partner_bonus']
                    pg_settings.steal_percent = settings['steal_percent']
                    pg_settings.steal_unlock_tasks = settings['steal_unlock_tasks']
            
            # 6. Sync Subgram exchanges
            sqlite_cursor.execute('''
            SELECT exchange_id, user_id, stars_amount, subgram_amount, 
                   exchange_date, status 
            FROM subgram_exchanges
            ''')
            exchanges = sqlite_cursor.fetchall()
            
            for exchange in exchanges:
                # Check if exchange exists in PostgreSQL
                pg_exchange = SubgramExchange.query.filter_by(id=exchange['exchange_id']).first()
                
                if pg_exchange:
                    # Update existing exchange
                    pg_exchange.user_id = exchange['user_id']
                    pg_exchange.stars_amount = exchange['stars_amount']
                    pg_exchange.subgram_amount = exchange['subgram_amount']
                    pg_exchange.status = exchange['status']
                    
                    if exchange['exchange_date']:
                        try:
                            pg_exchange.exchange_date = datetime.strptime(exchange['exchange_date'], '%Y-%m-%d %H:%M:%S')
                        except:
                            pg_exchange.exchange_date = datetime.now()
                else:
                    # Create new exchange
                    new_exchange = SubgramExchange(
                        id=exchange['exchange_id'],
                        user_id=exchange['user_id'],
                        stars_amount=exchange['stars_amount'],
                        subgram_amount=exchange['subgram_amount'],
                        status=exchange['status']
                    )
                    
                    if exchange['exchange_date']:
                        try:
                            new_exchange.exchange_date = datetime.strptime(exchange['exchange_date'], '%Y-%m-%d %H:%M:%S')
                        except:
                            new_exchange.exchange_date = datetime.now()
                    
                    db.session.add(new_exchange)
            
            # 7. Sync subscription rewards
            try:
                sqlite_cursor.execute('''
                SELECT id, user_id, channel_id, channel_name, stars_amount, reward_date 
                FROM subscription_rewards
                ''')
                rewards = sqlite_cursor.fetchall()
                
                for reward in rewards:
                    # Check if reward exists in PostgreSQL
                    pg_reward = SubscriptionReward.query.filter_by(id=reward['id']).first()
                    
                    if pg_reward:
                        # Update existing reward
                        pg_reward.user_id = reward['user_id']
                        pg_reward.channel_id = reward['channel_id']
                        pg_reward.channel_name = reward['channel_name']
                        pg_reward.stars_amount = reward['stars_amount']
                        
                        if reward['reward_date']:
                            try:
                                pg_reward.reward_date = datetime.strptime(reward['reward_date'], '%Y-%m-%d %H:%M:%S')
                            except:
                                pg_reward.reward_date = datetime.now()
                    else:
                        # Create new reward
                        new_reward = SubscriptionReward(
                            id=reward['id'],
                            user_id=reward['user_id'],
                            channel_id=reward['channel_id'],
                            channel_name=reward['channel_name'],
                            stars_amount=reward['stars_amount']
                        )
                        
                        if reward['reward_date']:
                            try:
                                new_reward.reward_date = datetime.strptime(reward['reward_date'], '%Y-%m-%d %H:%M:%S')
                            except:
                                new_reward.reward_date = datetime.now()
                        
                        db.session.add(new_reward)
            except Exception as e:
                logger.warning(f"Error syncing subscription rewards: {e}")
                # Continue with the sync even if this part fails
                
            # 8. Sync required channels
            try:
                sqlite_cursor.execute('''
                SELECT channel_id, channel_name, stars_reward, added_date 
                FROM required_channels
                ''')
                channels = sqlite_cursor.fetchall()
                
                for channel in channels:
                    # Check if channel exists in PostgreSQL
                    pg_channel = RequiredChannel.query.filter_by(channel_id=channel['channel_id']).first()
                    
                    if pg_channel:
                        # Update existing channel
                        pg_channel.channel_name = channel['channel_name']
                        pg_channel.stars_reward = channel['stars_reward']
                        
                        if channel['added_date']:
                            try:
                                pg_channel.added_date = datetime.strptime(channel['added_date'], '%Y-%m-%d %H:%M:%S')
                            except:
                                pg_channel.added_date = datetime.now()
                    else:
                        # Create new channel
                        new_channel = RequiredChannel(
                            channel_id=channel['channel_id'],
                            channel_name=channel['channel_name'],
                            stars_reward=channel['stars_reward']
                        )
                        
                        if channel['added_date']:
                            try:
                                new_channel.added_date = datetime.strptime(channel['added_date'], '%Y-%m-%d %H:%M:%S')
                            except:
                                new_channel.added_date = datetime.now()
                        
                        db.session.add(new_channel)
            except Exception as e:
                logger.warning(f"Error syncing required channels: {e}")
                # Continue with the sync even if this part fails
            
            # Commit all changes
            db.session.commit()
            
            logger.info("Database synchronization completed successfully!")
            
    except Exception as e:
        logger.error(f"Error syncing databases: {e}")
        if 'sqlite_conn' in locals():
            sqlite_conn.close()
        return False
    
    if 'sqlite_conn' in locals():
        sqlite_conn.close()
    
    return True


def sync_postgres_to_sqlite():
    """Synchronize data from PostgreSQL database to SQLite"""
    try:
        logger.info("Starting database synchronization from PostgreSQL to SQLite...")
        
        # Connect to SQLite database
        sqlite_conn = sqlite3.connect(DB_NAME)
        sqlite_cursor = sqlite_conn.cursor()
        
        with app.app_context():
            # 1. Get all users from PostgreSQL
            pg_users = User.query.all()
            pg_user_ids = set(user.user_id for user in pg_users)
            
            # 2. Get all users from SQLite
            sqlite_cursor.execute('SELECT user_id FROM users')
            sqlite_users = sqlite_cursor.fetchall()
            sqlite_user_ids = set(user[0] for user in sqlite_users)
            
            # 3. Find users that were deleted from PostgreSQL but still exist in SQLite
            deleted_user_ids = sqlite_user_ids - pg_user_ids
            
            # 4. Delete these users from SQLite
            for user_id in deleted_user_ids:
                logger.info(f"Deleting user {user_id} from SQLite (was deleted in PostgreSQL)")
                # Start a transaction
                sqlite_cursor.execute('BEGIN TRANSACTION')
                
                # Delete from user_tasks table
                sqlite_cursor.execute('DELETE FROM user_tasks WHERE user_id = ?', (user_id,))
                
                # Delete from withdrawals table
                sqlite_cursor.execute('DELETE FROM withdrawals WHERE user_id = ?', (user_id,))
                
                # Delete from game_stats table if exists
                try:
                    sqlite_cursor.execute('DELETE FROM game_stats WHERE user_id = ?', (user_id,))
                except sqlite3.OperationalError:
                    # Table might not exist, ignore
                    pass
                
                # Delete from subscription_rewards table
                sqlite_cursor.execute('DELETE FROM subscription_rewards WHERE user_id = ?', (user_id,))
                
                # Delete from subgram_exchanges table
                sqlite_cursor.execute('DELETE FROM subgram_exchanges WHERE user_id = ?', (user_id,))
                
                # Delete from subgram_offers table if exists
                try:
                    sqlite_cursor.execute('DELETE FROM subgram_offers WHERE user_id = ?', (user_id,))
                except sqlite3.OperationalError:
                    # Table might not exist, ignore
                    pass
                
                # Finally delete from users table
                sqlite_cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
                
                # Commit the transaction
                sqlite_cursor.execute('COMMIT')
            
            # 5. Update stars for existing users
            for user in pg_users:
                # Check if user exists in SQLite
                sqlite_cursor.execute('SELECT * FROM users WHERE user_id = ?', (user.user_id,))
                existing_user = sqlite_cursor.fetchone()
                
                if existing_user:
                    # Update existing user's stars in SQLite
                    sqlite_cursor.execute('''
                    UPDATE users 
                    SET stars = ?, 
                        is_banned = ? 
                    WHERE user_id = ?
                    ''', (user.stars, 1 if user.is_banned else 0, user.user_id))
            
            sqlite_conn.commit()
            logger.info("PostgreSQL to SQLite synchronization completed successfully!")
            
    except Exception as e:
        logger.error(f"Error during PostgreSQL to SQLite synchronization: {e}")
        if 'sqlite_conn' in locals():
            sqlite_conn.close()
        return False
    
    if 'sqlite_conn' in locals():
        sqlite_conn.close()
    
    return True


async def main():
    """Main function that runs the bot"""
    global should_exit
    
    try:
        # Check if we're shutting down
        if should_exit:
            logger.info("Shutdown requested, not starting bot")
            return True
            
        # Delete webhook before polling
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Synchronize databases if they exist
        try:
            sync_sqlite_to_postgres()
        except Exception as db_error:
            logger.error(f"Database synchronization error: {db_error}")
            logger.warning("Continuing without database synchronization")
        
        logger.info("Starting bot...")
        
        # Create a task to check the shutdown flag periodically
        async def check_shutdown():
            while True:
                if should_exit:
                    logger.info("Shutdown flag detected, stopping polling...")
                    
                    # Try to gracefully stop polling
                    try:
                        await bot.session.close()
                    except Exception as e:
                        logger.error(f"Error closing bot session: {e}")
                        
                    # Stop the event loop
                    asyncio.get_event_loop().stop()
                    break
                
                await asyncio.sleep(2)  # Check every 2 seconds
                
        # Start the shutdown checker in background
        asyncio.create_task(check_shutdown())
        
        # Start polling with recovery
        try:
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        except Exception as polling_error:
            logger.error(f"Polling error: {polling_error}")
            # Try to reconnect if it's a connection error
            if "Connection" in str(polling_error) or "Network" in str(polling_error):
                logger.warning("Connection issue detected, will retry...")
                await asyncio.sleep(10)
                return False
            else:
                # Re-raise non-connection errors
                raise
        
        return True
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        # Wait before retrying to avoid rapid restarts
        await asyncio.sleep(5)
        return False

async def run_bot_with_restart():
    """Run the bot with automatic restart on failure"""
    max_consecutive_errors = 5
    consecutive_errors = 0
    error_cooldown = 10  # Initial cooldown in seconds
    
    while True:
        try:
            # Reset error count after successful period
            if consecutive_errors > 0 and consecutive_errors < max_consecutive_errors:
                logger.info("Bot has been stable, resetting error counter")
                consecutive_errors = 0
                error_cooldown = 10
            
            result = await main()
            if not result:
                consecutive_errors += 1
                # Exponential backoff for repeated errors
                error_cooldown = min(error_cooldown * 1.5, 300)  # Max 5 minutes
                
                logger.warning(f"Bot exited with error ({consecutive_errors}/{max_consecutive_errors}), "
                               f"restarting in {int(error_cooldown)} seconds...")
                
                await asyncio.sleep(error_cooldown)
                
                # If too many consecutive errors, log but continue trying
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("Multiple consecutive failures detected!")
                    logger.info("Bot will continue to retry but may need manual intervention")
            else:
                # If main() returns True, bot was stopped cleanly
                break
                
        except Exception as e:
            consecutive_errors += 1
            logger.error(f"Unhandled exception: {e}")
            logger.warning(f"Restarting bot in {int(error_cooldown)} seconds...")
            await asyncio.sleep(error_cooldown)

if __name__ == "__main__":
    # Configure signal handlers
    import signal
    
    def signal_handler(sig, frame):
        """Handle termination signals"""
        logger.info(f"Received signal {sig}, shutting down gracefully...")
        
        # Set flag for graceful shutdown
        global should_exit
        should_exit = True
        
        # Close database connections
        try:
            if 'sqlite_conn' in globals() and sqlite_conn:
                logger.info("Closing SQLite connection...")
                sqlite_conn.close()
        except Exception as e:
            logger.error(f"Error closing SQLite connection: {e}")
            
        # Close the bot session if possible
        try:
            if 'bot' in globals() and bot:
                logger.info("Closing bot session...")
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(bot.session.close())
        except Exception as e:
            logger.error(f"Error closing bot session: {e}")
            
        # Stop the event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                logger.info("Stopping event loop...")
                loop.stop()
        except Exception as e:
            logger.error(f"Error stopping event loop: {e}")
            
        logger.info("Bot shutdown initiated, waiting for tasks to complete...")
        
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Run the bot with automatic restart
        asyncio.run(run_bot_with_restart())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user!")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
