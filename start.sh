#!/bin/bash

# Script to prepare and run the Telegram analysis bot.
# This script is designed to be managed by a process manager like pm2.
# It ensures the environment is set up and then runs the bot in the foreground.

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

echo ">>> 2. Pulling latest changes from Git..."
git pull

echo ">>> 3. Installing/Updating dependencies into the virtual environment..."
$PIP_EXEC install -r requirements.txt

echo ">>> 4. Starting bot process in the foreground (for pm2 to manage)..."
# The 'exec' command replaces the shell process with the Python process.
# This is the correct way to hand over control to a process manager like pm2.
exec $PYTHON_EXEC main.py