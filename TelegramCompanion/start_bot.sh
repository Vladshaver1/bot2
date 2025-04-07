#!/bin/bash

# Script to start and keep the Telegram bot running
# Usage: ./start_bot.sh [start|stop|restart|status]

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PYTHON_CMD="python3"
BOT_SCRIPT="main.py"
WATCHDOG_SCRIPT="watchdog.py"
PID_FILE="${SCRIPT_DIR}/bot.pid"
LOG_FILE="${SCRIPT_DIR}/logs/bot_startup.log"

# Ensure logs directory exists
mkdir -p "${SCRIPT_DIR}/logs"

# Function to log messages
log() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "${timestamp} - $1" | tee -a "${LOG_FILE}"
}

# Function to check if the bot is running
is_running() {
    if [ -f "${PID_FILE}" ]; then
        local pid=$(cat "${PID_FILE}")
        if ps -p "${pid}" > /dev/null; then
            return 0  # Running
        fi
    fi
    return 1  # Not running
}

# Function to start the bot using the watchdog
start_bot() {
    if is_running; then
        log "Bot is already running with PID $(cat ${PID_FILE})"
        return 0
    fi
    
    log "Starting bot with watchdog..."
    cd "${SCRIPT_DIR}"
    
    # Start the watchdog in the background
    nohup ${PYTHON_CMD} ${WATCHDOG_SCRIPT} > "${SCRIPT_DIR}/logs/watchdog_output.log" 2>&1 &
    local pid=$!
    
    echo ${pid} > "${PID_FILE}"
    log "Watchdog started with PID ${pid}"
    sleep 2
    
    if is_running; then
        log "Bot successfully started"
        return 0
    else
        log "Failed to start bot"
        return 1
    fi
}

# Function to stop the bot
stop_bot() {
    if ! is_running; then
        log "Bot is not running"
        return 0
    fi
    
    local pid=$(cat "${PID_FILE}")
    log "Stopping bot with PID ${pid}..."
    
    # Send SIGTERM to the watchdog process
    kill -15 "${pid}" 2>/dev/null
    
    # Wait for up to 10 seconds for graceful shutdown
    local count=0
    while is_running && [ ${count} -lt 10 ]; do
        sleep 1
        ((count++))
    done
    
    # If still running, force kill
    if is_running; then
        log "Force killing bot process..."
        kill -9 "${pid}" 2>/dev/null
    fi
    
    rm -f "${PID_FILE}"
    log "Bot stopped"
    return 0
}

# Function to restart the bot
restart_bot() {
    log "Restarting bot..."
    stop_bot
    sleep 2
    start_bot
}

# Function to check bot status
check_status() {
    if is_running; then
        log "Bot is running with PID $(cat ${PID_FILE})"
        return 0
    else
        log "Bot is not running"
        return 1
    fi
}

# Main script logic
case "$1" in
    start)
        start_bot
        ;;
    stop)
        stop_bot
        ;;
    restart)
        restart_bot
        ;;
    status)
        check_status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac

exit $?