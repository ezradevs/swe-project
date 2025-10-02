#!/bin/bash

# run.sh - Utility script to stop any running Flask app, create virtual environment, install dependencies, and start the Flask server.
# Usage: chmod +x run.sh | ./run.sh

echo "Stopping any existing Flask processes..."
ps aux | grep app.py | grep -v grep | awk '{print $2}' | xargs -r kill
echo "Creating virtual environment..."
python3 -m venv .venv
echo "Activating virtual environment..."
source .venv/bin/activate
echo "Updating pip..."
pip3 install --upgrade pip
echo "Installing required Python packages..."
pip3 install -r requirements.txt
# --- Security configuration (hardcoded for convenience) ---
# NOTE: These secrets are embedded in this file for your local use.
# Do NOT commit or share this file if publishing your code.
export APP_ENV=production
export FLASK_SECRET_KEY='bcbbe90a8917b0a1dcffd22d09c80b652e2c3891a82f0447'
export ADMIN_DELETE_CODE='F1Mwg-x7VkB64UrMMpm09sNEvVf_Lgy1'
# Optional: enable invite-only admin signup by uncommenting the next line
export ADMIN_SIGNUP_SECRET='4WDidHzh09YXpg'

echo "Starting Flask app..."
python3 app.py
