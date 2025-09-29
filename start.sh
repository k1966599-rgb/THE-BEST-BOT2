#!/bin/bash

# Script to gracefully stop, update, and restart the Telegram analysis bot.

BOT_PROCESS_NAME="python main.py"
LOG_FILE="bot.log"

echo ">>> 1. Attempting to stop any existing bot process..."
# Find the process ID (PID) of the bot. The `grep -v grep` part is to exclude the grep process itself.
PID=$(ps aux | grep "$BOT_PROCESS_NAME" | grep -v grep | awk '{print $2}')

if [ -n "$PID" ]; then
    echo "    - Bot process found with PID: $PID. Stopping it now."
    kill $PID
    # Wait a moment for the process to terminate
    sleep 2
    echo "    - Process stopped."
else
    echo "    - No running bot process found. Continuing."
fi

echo ">>> 2. Pulling latest changes from Git..."
git pull

echo ">>> 3. Installing/Updating dependencies from requirements.txt..."
pip install -r requirements.txt

echo ">>> 4. Starting the bot in the background..."
# Use nohup to keep the process running after the terminal is closed.
# Redirect stdout and stderr to a log file.
nohup python main.py > $LOG_FILE 2>&1 &

echo ">>> Bot has been started successfully."
echo ">>> You can view the logs by running: tail -f $LOG_FILE"
echo ">>> To stop the bot, run this script again or use 'pkill -f \"$BOT_PROCESS_NAME\"'"