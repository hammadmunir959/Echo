# Define virtual environment directory
$VENV_DIR = "venv"

# Check if venv exists
if (-not (Test-Path "$VENV_DIR")) {
    Write-Host "Creating virtual environment..."
    python -m venv $VENV_DIR
}

# Activate venv
$ActivateScript = "$VENV_DIR\Scripts\Activate.ps1"
if (Test-Path $ActivateScript) {
    . $ActivateScript
} else {
    Write-Error "Cannot find activate script at $ActivateScript"
    exit 1
}

# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
if (Test-Path "requirements.txt") {
    Write-Host "Installing requirements..."
    pip install -r requirements.txt
} else {
    Write-Warning "requirements.txt not found."
}

# Run interactive test
Write-Host "Starting Project Echo - Interactive Test Mode..."
python runners\interactive_test.py
