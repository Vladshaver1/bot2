#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("watchdog.log")
    ]
)
logger = logging.getLogger("watchdog")

# Configuration
BOT_SCRIPT = "main.py"  # Main bot script to run
CHECK_INTERVAL = 30     # How often to check if the bot is running (seconds)
MAX_RESTART_ATTEMPTS = 5  # Maximum number of restart attempts before giving up
RESTART_COOLDOWN = 60    # Cooldown between restart attempts (seconds)

def get_timestamp():
    """Get current timestamp string"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def is_process_running(process):
    """Check if the process is still running"""
    if process is None:
        return False
    
    return process.poll() is None

def start_bot():
    """Start the bot process"""
    logger.info(f"Starting bot: python {BOT_SCRIPT}")
    
    try:
        # Start the bot as a subprocess
        process = subprocess.Popen(
            ["python", BOT_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        logger.info(f"Bot started with PID: {process.pid}")
        return process
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        return None

def log_output(process):
    """Read and log output from the bot process"""
    if process is None:
        return
    
    # Check if there's any output to read
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            # Log the bot's output, but strip any control characters
            clean_output = output.strip()
            if clean_output:
                logger.info(f"BOT: {clean_output}")

def main():
    """Main watchdog function"""
    logger.info("=== Bot Watchdog Started ===")
    
    bot_process = None
    restart_count = 0
    last_restart_time = 0
    
    try:
        while True:
            current_time = time.time()
            
            # Check if the bot is running
            if bot_process is None or not is_process_running(bot_process):
                # If this is a restart and we need to wait for cooldown
                if bot_process is not None and (current_time - last_restart_time) < RESTART_COOLDOWN:
                    logger.info(f"Waiting for restart cooldown ({RESTART_COOLDOWN} seconds)...")
                    time.sleep(RESTART_COOLDOWN - (current_time - last_restart_time))
                
                # Check if we've exceeded the maximum restart attempts
                if restart_count >= MAX_RESTART_ATTEMPTS:
                    logger.error(f"Exceeded maximum restart attempts ({MAX_RESTART_ATTEMPTS}).")
                    logger.error("Please check the bot for errors and restart manually.")
                    
                    # Reset the restart counter after a longer wait
                    time.sleep(RESTART_COOLDOWN * 3)
                    restart_count = 0
                
                # Start or restart the bot
                if bot_process is None:
                    logger.info("Initial bot start")
                else:
                    logger.warning("Bot is not running, restarting...")
                    restart_count += 1
                
                bot_process = start_bot()
                last_restart_time = time.time()
            
            # Log any output from the bot
            log_output(bot_process)
            
            # Wait before checking again
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("Watchdog received interrupt signal, shutting down...")
        if bot_process is not None and is_process_running(bot_process):
            logger.info(f"Terminating bot process (PID: {bot_process.pid})")
            bot_process.terminate()
            # Give it a moment to terminate gracefully
            time.sleep(3)
            # Force kill if still running
            if is_process_running(bot_process):
                logger.info("Bot did not terminate gracefully, forcing...")
                bot_process.kill()
    
    logger.info("=== Bot Watchdog Stopped ===")

if __name__ == "__main__":
    main()