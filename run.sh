#!/bin/bash

# run.sh - Utility script to stop any running Flask app, create virtual environment, install dependencies, and start the Flask server.
# Usage: chmod +x run.sh | ./run.sh

echo "Stopping any existing Flask processes..."
ps aux | grep app.py | grep -v grep | awk '{print $2}' | xargs -r kill
echo "Creating virtual environment..."
python3 -m venv venv
echo "Activating virtual environment..."
source venv/bin/activate
echo "Updating pip..."
pip3 install --upgrade pip
echo "Installing required Python packages..."
pip3 install -r requirements.txt
echo "Starting Flask app..."
python3 app.py