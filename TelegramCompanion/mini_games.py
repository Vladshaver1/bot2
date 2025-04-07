import random
import logging
from config import DICE_REWARD, SLOTS_REWARD, GAME_DAILY_LIMIT

logger = logging.getLogger(__name__)

class Games:
    def __init__(self, db):
        self.db = db
    
    async def play_dice(self, user_id):
        """
        Play a dice game
        Returns: (can_play, result, reward)
        """
        try:
            # Check daily game limit
            daily_games = self.db.get_user_game_stats(user_id)
            
            if daily_games >= GAME_DAILY_LIMIT:
                return False, None, 0
            
            # Increment game counter
            self.db.increment_game_counter(user_id)
            
            # Roll the dice
            dice_result = random.randint(1, 6)
            
            # Calculate reward
            reward = DICE_REWARD.get(dice_result, 0)
            
            # Add stars to user
            if reward > 0:
                self.db.update_user_stars(user_id, reward)
            
            return True, dice_result, reward
        except Exception as e:
            logger.error(f"Error in play_dice: {e}")
            return False, None, 0
    
    async def play_slots(self, user_id):
        """
        Play a slot machine game
        Returns: (can_play, symbols, reward)
        """
        try:
            # Check daily game limit
            daily_games = self.db.get_user_game_stats(user_id)
            
            if daily_games >= GAME_DAILY_LIMIT:
                return False, None, 0
            
            # Increment game counter
            self.db.increment_game_counter(user_id)
            
            # Possible symbols
            symbols = ['🍒', '🍋', '7️⃣', '💎']
            weights = [0.5, 0.3, 0.15, 0.05]  # Weights for each symbol
            
            # Spin the slots
            result = []
            for _ in range(3):
                result.append(random.choices(symbols, weights=weights)[0])
            
            # Calculate reward
            reward = 0
            if result.count(result[0]) == 3:  # All three symbols match
                reward = SLOTS_REWARD.get(result[0], 0)
            
            # Add stars to user
            if reward > 0:
                self.db.update_user_stars(user_id, reward)
            
            return True, result, reward
        except Exception as e:
            logger.error(f"Error in play_slots: {e}")
            return False, None, 0
    
    async def play_steal(self, thief_id, victim_id):
        """
        Attempt to steal stars from another user
        Returns: (success, amount_stolen)
        """
        try:
            # Check if thief has completed enough tasks
            thief_stats = self.db.get_user_stats(thief_id)
            settings = self.db.get_admin_settings()
            
            if not thief_stats or not settings:
                return False, 0
            
            stars, completed_tasks, _ = thief_stats
            _, _, _, steal_percent, steal_unlock_tasks = settings
            
            # Check if user has unlocked stealing ability
            if completed_tasks < steal_unlock_tasks:
                return False, 0
            
            # Check daily game limit
            daily_games = self.db.get_user_game_stats(thief_id)
            if daily_games >= GAME_DAILY_LIMIT:
                return False, 0
            
            # Increment game counter
            self.db.increment_game_counter(thief_id)
            
            # Calculate amount to steal
            victim_stats = self.db.get_user_stats(victim_id)
            if not victim_stats:
                return False, 0
                
            victim_stars = victim_stats[0]
            
            # Calculate steal amount based on percentage
            steal_amount = int(victim_stars * (steal_percent / 100))
            
            # Minimum 1 star if victim has stars
            if victim_stars > 0 and steal_amount == 0:
                steal_amount = 1
            
            # Execute the theft
            stolen = self.db.steal_stars(thief_id, victim_id, steal_amount)
            
            return stolen > 0, stolen
        except Exception as e:
            logger.error(f"Error in play_steal: {e}")
            return False, 0
