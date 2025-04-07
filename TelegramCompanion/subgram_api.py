import aiohttp
import logging

logger = logging.getLogger(__name__)

class SubgramAPI:
    BASE_URL = "https://api.subgram.ru"
    
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.session = None
    
    async def _ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers={"Auth": self.api_key})
        return self.session
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _make_request(self, method, endpoint, data=None, params=None):
        session = await self._ensure_session()
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            if method == "GET":
                async with session.get(url, params=params) as response:
                    response_data = await response.json()
            elif method == "POST":
                async with session.post(url, json=data) as response:
                    response_data = await response.json()
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            if response.status != 200:
                logger.error(f"Subgram API error: {response.status} - {response_data}")
                return None
            
            return response_data
        except Exception as e:
            logger.error(f"Error making request to Subgram API: {e}")
            return None
    
    async def get_user_info(self, telegram_id):
        """Get Subgram user information by Telegram ID"""
        endpoint = "/integration/user-info"
        params = {"telegram_id": telegram_id}
        return await self._make_request("GET", endpoint, params=params)
    
    async def create_transaction(self, user_id, amount, description="Stars exchange"):
        """Create a transaction for a user"""
        endpoint = "/integration/create-transaction"
        data = {
            "user_id": user_id,
            "amount": amount,
            "description": description
        }
        return await self._make_request("POST", endpoint, data=data)
    
    async def get_user_balance(self, user_id):
        """Get user balance"""
        endpoint = "/integration/user-balance"
        params = {"user_id": user_id}
        response = await self._make_request("GET", endpoint, params=params)
        if response and isinstance(response, dict) and "balance" in response:
            return response["balance"]
        return None
    
    async def check_subscription(self, user_id, channel_id):
        """Check if user is subscribed to a channel"""
        endpoint = "/integration/check-subscription"
        params = {
            "user_id": user_id,
            "channel_id": channel_id
        }
        response = await self._make_request("GET", endpoint, params=params)
        if response and isinstance(response, dict) and "is_subscribed" in response:
            return response["is_subscribed"]
        return False
    
    async def register_user(self, telegram_id, username=None, first_name=None, last_name=None):
        """Register a new user in Subgram"""
        endpoint = "/integration/register-user"
        data = {
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name
        }
        return await self._make_request("POST", endpoint, data=data)
    
    # Методы для работы с обязательными подписками (ОП)
    async def get_required_channels(self):
        """Get list of channels that require subscription"""
        endpoint = "/integration/required-channels"
        return await self._make_request("GET", endpoint)
    
    async def add_required_channel(self, channel_id, channel_name, stars_reward=10):
        """Add a new channel to required subscriptions list"""
        endpoint = "/integration/add-required-channel"
        data = {
            "channel_id": channel_id,
            "channel_name": channel_name,
            "stars_reward": stars_reward
        }
        return await self._make_request("POST", endpoint, data=data)
    
    async def remove_required_channel(self, channel_id):
        """Remove a channel from required subscriptions list"""
        endpoint = "/integration/remove-required-channel"
        data = {
            "channel_id": channel_id
        }
        return await self._make_request("POST", endpoint, data=data)
    
    async def check_required_subscriptions(self, user_id):
        """Check if user is subscribed to all required channels"""
        endpoint = "/integration/check-required-subscriptions"
        params = {"user_id": user_id}
        return await self._make_request("GET", endpoint, params=params)
    
    async def reward_for_subscription(self, user_id, channel_id):
        """Reward user for subscribing to a channel"""
        endpoint = "/integration/reward-subscription"
        data = {
            "user_id": user_id,
            "channel_id": channel_id
        }
        return await self._make_request("POST", endpoint, data=data)
    
    async def get_balance(self):
        """
        Получение актуального баланса пользователя из Subgram API
        
        Returns:
            tuple: (status, code, message, balance)
                status - 'ok', 'error'
                code - HTTP код ответа
                message - Сообщение от сервиса
                balance - Актуальный баланс пользователя в рублях (если статус 'ok')
        """
        endpoint = "/get-balance"
        headers = {"Auth": self.api_key}
        
        try:
            url = f"{self.BASE_URL}{endpoint}"
            
            # Создаем новую сессию для запроса
            async with aiohttp.ClientSession() as session:
                logger.info(f"Requesting balance from {url}")
                
                # Отправляем POST запрос с заголовком Auth
                async with session.post(url, headers=headers) as response:
                    try:
                        response_data = await response.json()
                        logger.info(f"Balance response status: {response.status}")
                    except Exception as json_err:
                        logger.error(f"Failed to parse JSON response: {json_err}")
                        response_text = await response.text()
                        logger.error(f"Response text: {response_text}")
                        return "error", response.status, f"Invalid JSON response", 0.0
                    
                    # Извлекаем данные из ответа
                    status = response_data.get("status")
                    code = response_data.get("code")
                    message = response_data.get("message", "")
                    balance = response_data.get("balance", 0.0)
                    
                    logger.info(f"Parsed balance response: status={status}, code={code}, balance={balance}")
                    return status, code, message, balance
                
        except Exception as e:
            logger.error(f"Error requesting Subgram balance: {e}")
            return "error", 500, str(e), 0.0
            
    async def get_statistics(self, period=30):
        """
        Получение статистики бота из Subgram API
        
        Args:
            period (int): Количество дней для анализа статистики (по умолчанию 30)
            
        Returns:
            tuple: (status, code, message, data, summary)
                status - 'ok', 'error'
                code - HTTP код ответа
                message - Сообщение от сервиса
                data - Массив данных статистики (если статус 'ok')
                summary - Словарь с суммарной статистикой
        """
        endpoint = "/get-statistic"
        headers = {"Auth": self.api_key}
        
        try:
            url = f"{self.BASE_URL}{endpoint}"
            
            # Создаем новую сессию для запроса
            async with aiohttp.ClientSession() as session:
                logger.info(f"Requesting statistics from {url}")
                
                # Отправляем POST запрос с заголовком Auth
                async with session.post(url, headers=headers) as response:
                    try:
                        response_data = await response.json()
                        logger.info(f"Statistics response status: {response.status}")
                    except Exception as json_err:
                        logger.error(f"Failed to parse JSON response: {json_err}")
                        response_text = await response.text()
                        logger.error(f"Response text: {response_text}")
                        return "error", response.status, f"Invalid JSON response", [], {}
                    
                    # Извлекаем данные из ответа
                    status = response_data.get("status")
                    code = response_data.get("code")
                    message = response_data.get("message", "")
                    data = response_data.get("data", [])
                    
                    # Ограничиваем данные запрошенным периодом
                    data = data[:period] if period and len(data) > period else data
                    
                    # Подготавливаем сводную информацию
                    summary = {}
                    if status == "ok" and data:
                        # Общая статистика
                        total_count = sum(entry.get("count", 0) for entry in data)
                        total_amount = sum(entry.get("amount", 0) for entry in data)
                        
                        # Статистика за последнюю неделю
                        week_data = data[:7] if len(data) >= 7 else data
                        week_count = sum(entry.get("count", 0) for entry in week_data)
                        week_amount = sum(entry.get("amount", 0) for entry in week_data)
                        
                        # Статистика за последний день
                        day_count = data[0].get("count", 0) if data else 0
                        day_amount = data[0].get("amount", 0) if data else 0
                        
                        # Средние значения
                        avg_count = total_count / len(data) if data else 0
                        avg_amount = total_amount / len(data) if data else 0
                        
                        summary = {
                            "total_count": total_count,
                            "total_amount": total_amount,
                            "week_count": week_count,
                            "week_amount": week_amount,
                            "day_count": day_count,
                            "day_amount": day_amount,
                            "avg_count": avg_count,
                            "avg_amount": avg_amount,
                            "days_analyzed": len(data)
                        }
                    
                    logger.info(f"Parsed statistics response: status={status}, code={code}")
                    return status, code, message, data, summary
                
        except Exception as e:
            logger.error(f"Error requesting Subgram statistics: {e}")
            return "error", 500, str(e), [], {}
    
    async def get_sponsor_tasks(self, user_id, chat_id, limit=5):
        """
        Получение списка заданий от спонсоров Subgram
        
        Args:
            user_id: ID пользователя в Telegram
            chat_id: ID чата в котором происходит взаимодействие
            limit: Максимальное количество заданий для получения (1-10)
            
        Returns:
            tuple: (status, code, message, tasks)
                status - 'ok', 'error'
                code - HTTP код ответа
                message - Сообщение от сервиса
                tasks - Список заданий от спонсоров (список словарей с данными заданий)
        """
        try:
            headers = {
                'Content-Type': 'application/json',
                'Auth': self.api_key,
                'Accept': 'application/json',
            }
            
            data = {
                'UserId': str(user_id), 
                'ChatId': str(chat_id)
            }
            
            if limit is not None:
                data["Limit"] = str(limit)
            
            url = f"{self.BASE_URL}/request-op/"
            logger.info(f"Requesting sponsor tasks using request-op endpoint: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if not response.ok:
                        logger.error(f"SubGram error: {response.status}")
                        try:
                            error_data = await response.json()
                            logger.error(f"SubGram error: {error_data}")
                        except:
                            logger.error(f"Unable to parse error response")
                        return 'ok', 400, "Error", []
                    
                    try:
                        response_data = await response.json()
                        logger.info(f"Sponsor tasks response status: {response.status}")
                    except Exception as json_err:
                        logger.error(f"Failed to parse JSON response: {json_err}")
                        return "error", response.status, f"Invalid JSON response", []
                    
                    # Извлекаем данные из ответа
                    status = response_data.get("status", "ok")
                    code = response_data.get("code", 200)
                    message = response_data.get("message", "")
                    tasks = response_data.get("data", [])
                    
                    logger.info(f"Parsed sponsor tasks response: status={status}, code={code}, tasks={len(tasks) if tasks else 0}")
                    return status, code, message, tasks
        
        except Exception as e:
            logger.error(f"Error requesting Subgram sponsor tasks: {e}")
            return "ok", 400, str(e), []
    
    async def request_op(self, user_id, chat_id, gender=None, first_name=None, language_code=None, is_premium=None, max_op=None):
        """
        Запрос к Subgram API для проверки подписок пользователя и получения ссылок на обязательные каналы
        
        Args:
            user_id: ID пользователя в Telegram
            chat_id: ID чата в котором происходит взаимодействие
            gender: Пол пользователя ('male' или 'female'), если известен
            first_name: Имя пользователя (требуется если бот добавлен без токена)
            language_code: Код языка пользователя (требуется если бот добавлен без токена)
            is_premium: Статус премиум пользователя (требуется если бот добавлен без токена)
            max_op: Максимальное количество спонсоров в запросе (1-10)
            
        Returns:
            tuple: (status, code, message, links)
                status - 'ok', 'warning', 'gender', 'error'
                code - HTTP код ответа
                message - Сообщение от сервиса
                links - Список ссылок для подписки (если есть)
        """
        try:
            headers = {
                'Content-Type': 'application/json',
                'Auth': self.api_key,
                'Accept': 'application/json',
            }
            
            data = {
                'UserId': str(user_id), 
                'ChatId': str(chat_id)
            }
            
            # Добавляем опциональные параметры
            if gender is not None:
                data["Gender"] = gender
            if first_name is not None:
                data["first_name"] = first_name
            if language_code is not None:
                data["language_code"] = language_code
            if is_premium is not None:
                data["Premium"] = is_premium
            if max_op is not None:
                data["MaxOP"] = str(max_op)
            
            url = f"{self.BASE_URL}/request-op/"
            logger.info(f"Sending request to {url} with data: {data}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if not response.ok:
                        logger.error(f"SubGram error: {response.status}")
                        try:
                            error_data = await response.json()
                            logger.error(f"SubGram error: {error_data}")
                        except:
                            logger.error(f"Unable to parse error response")
                        return 'ok', 400, "Error", []
                    
                    try:
                        response_data = await response.json()
                        logger.info(f"Response status: {response.status}, data: {response_data}")
                    except Exception as json_err:
                        logger.error(f"Failed to parse JSON response: {json_err}")
                        return "error", response.status, f"Invalid JSON response", []
                    
                    # Извлекаем нужные данные из ответа
                    status = response_data.get("status")
                    code = response_data.get("code")
                    message = response_data.get("message", "")
                    links = response_data.get("links", [])
                    
                    # Если статус не указан, это ошибка API
                    if not status:
                        logger.warning("Missing status in response from Subgram API")
                        status = "error"
                        code = response.status
                        message = "Invalid response from Subgram API: missing status field"
                    
                    logger.info(f"Parsed Subgram response: status={status}, code={code}")
                    return status, code, message, links
        
        except Exception as e:
            logger.error(f"SubGram request_op error: {str(e)}")
            return 'ok', 400, "Error", []

# Create a singleton instance with API key from config
from config import SUBGRAM_API_KEY
subgram_api = SubgramAPI(api_key=SUBGRAM_API_KEY)