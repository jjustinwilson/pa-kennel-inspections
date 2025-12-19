#!/bin/bash
# Start the Kennel Inspection Web Application

cd /Users/jjustinwilson/Desktop/kennel
source venv/bin/activate

echo "Starting PA Kennel Inspection Web Application..."
echo "Access at: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python app.py
