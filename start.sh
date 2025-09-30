#!/bin/bash

# Script to gracefully stop, update, and restart the Telegram analysis bot
# using a Python virtual environment.

BOT_PROCESS_NAME="python main.py"
LOG_FILE="bot.log"
VENV_DIR="venv"

echo ">>> 1. Checking for Virtual Environment..."
if [ ! -d "$VENV_DIR" ]; then
    echo "    - Virtual environment not found. Creating one at '$VENV_DIR/'..."
    python3 -m venv $VENV_DIR
    if [ $? -ne 0 ]; then
        echo "    - ERROR: Failed to create virtual environment. Please ensure 'python3-venv' is installed."
        exit 1
    fi
    echo "    - Virtual environment created successfully."
else
    echo "    - Virtual environment found."
fi

# Define paths to python and pip within the venv
PYTHON_EXEC="$VENV_DIR/bin/python"
PIP_EXEC="$VENV_DIR/bin/pip"

echo ">>> 2. Attempting to stop any existing bot process..."
# Find the process ID (PID) of the bot. The `grep -v grep` part is to exclude the grep process itself.
# We also look for the venv path to be more specific.
PID=$(ps aux | grep "$VENV_DIR/bin/python main.py" | grep -v grep | awk '{print $2}')

if [ -n "$PID" ]; then
    echo "    - Bot process found with PID: $PID. Stopping it now."
    kill $PID
    # Wait a moment for the process to terminate
    sleep 2
    echo "    - Process stopped."
else
    echo "    - No running bot process found. Continuing."
fi

echo ">>> 3. Pulling latest changes from Git..."
git pull

echo ">>> 4. Installing/Updating dependencies into the virtual environment..."
$PIP_EXEC install -r requirements.txt

echo ">>> 5. Starting the bot in the background using the virtual environment..."
# Use nohup to keep the process running after the terminal is closed.
# Redirect stdout and stderr to a log file.
nohup $PYTHON_EXEC main.py > $LOG_FILE 2>&1 &

echo ">>> Bot has been started successfully."
echo ">>> You can view the logs by running: tail -f $LOG_FILE"
echo ">>> To stop the bot, run this script again or use 'pkill -f \"$BOT_PROCESS_NAME\"'"