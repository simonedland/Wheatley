# Check if python is available
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python is not installed or not in PATH. Exiting."
    exit 1
}

# Check for .venv folder; create if missing
if (!(Test-Path ".\.venv")) {
    Write-Host "Virtual environment .venv not found. Creating one..."
    python -m venv .\.venv
} else {
    Write-Host "Virtual environment .venv already exists."
}

# Activate the virtual environment
Write-Host "Activating virtual environment..."
& .\.venv\Scripts\Activate.ps1

# Install prerequisites by running the install_prerequisites.py script
Write-Host "Installing prerequisites..."
python install_prerequisites.py

# Check that the config file exists
$configPath = "Wheatly/python/src/config/config.yaml"
if (Test-Path $configPath) {
    Write-Host "Configuration file found: $configPath"
} else {
    Write-Host "Configuration file not found: $configPath. Exiting."
    exit 1
}

# Run test.py to execute tests
Write-Host "Running tests..."
python Wheatly/python/src/test.py
