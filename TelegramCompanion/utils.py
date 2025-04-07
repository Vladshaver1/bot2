import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

logger = logging.getLogger(__name__)

def setup_logging(log_to_file=True):
    """
    Configure logging with enhanced options
    
    Args:
        log_to_file: Whether to also log to a rotating file
    """
    # Create logs directory if it doesn't exist
    if log_to_file and not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Console handler for all logs
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for persistent logs
    if log_to_file:
        file_handler = RotatingFileHandler(
            'logs/bot.log',
            maxBytes=5*1024*1024,  # 5MB
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # Separate error log
        error_handler = RotatingFileHandler(
            'logs/error.log',
            maxBytes=2*1024*1024,  # 2MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        error_handler.setFormatter(error_formatter)
        root_logger.addHandler(error_handler)
    
    # Disable other loggers
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    
    logger.info("Enhanced logging configured")

def get_current_time():
    """Get current time in formatted string"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def format_number(number):
    """Format large numbers with thousand separators"""
    return '{:,}'.format(number).replace(',', ' ')

def calculate_time_difference(date_string):
    """Calculate time difference between now and given date string"""
    if not date_string:
        return "неизвестно"
        
    try:
        date_format = "%Y-%m-%d %H:%M:%S"
        past_date = datetime.strptime(date_string, date_format)
        now = datetime.now()
        
        delta = now - past_date
        
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            return f"{days} д. {hours} ч."
        elif hours > 0:
            return f"{hours} ч. {minutes} мин."
        elif minutes > 0:
            return f"{minutes} мин."
        else:
            return "менее минуты"
    except Exception as e:
        logger.error(f"Error in calculate_time_difference: {e}")
        return "ошибка"
