#!/bin/bash

# Setup script for receipt processing environment

echo "Setting up virtual environment for receipt processing..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "Setup complete!"
echo ""
echo "To use the receipt processor:"
echo "  1. Activate the virtual environment: source venv/bin/activate"
echo "  2. Run the script: ./receiptprocess.py <directory>"
echo "  3. When done, deactivate: deactivate"
