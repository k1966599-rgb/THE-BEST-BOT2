#!/bin/bash

# Script to update and run the Telegram analysis bot

echo ">>> 1. Pulling latest changes from Git..."
git pull

echo ">>> 2. Installing/Updating dependencies from requirements.txt..."
pip install -r requirements.txt

echo ">>> 3. Starting the bot..."
python src/telegram_bot.py

echo ">>> Bot has been started."