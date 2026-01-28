#!/bin/bash

# Define virtual environment directory
VENV_DIR="venv"

# Check if venv exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python -m venv $VENV_DIR
fi

# Activate venv
# Handle Windows (Scripts) and Unix (bin) paths
if [ -f "$VENV_DIR/Scripts/activate" ]; then
    source "$VENV_DIR/Scripts/activate"
elif [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
else
    echo "Error: Cannot find activate script in $VENV_DIR"
    exit 1
fi

# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
if [ -f "requirements.txt" ]; then
    echo "Installing requirements..."
    pip install -r requirements.txt
else
    echo "Warning: requirements.txt not found."
fi

# Run interactive test
echo "Starting Project Echo - Interactive Test Mode..."
python runners/interactive_test.py
