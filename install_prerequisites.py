"""Install packages listed in ``requirements.txt`` with progress output."""

import subprocess
import sys
import os
import time


def install_requirements():
    """Install packages listed in requirements.txt with progress output."""
    # Path to the requirements file inside the Wheatley project folder
    req_file = os.path.join(os.path.dirname(__file__), "wheatley", "requirements.txt")
    if not os.path.exists(req_file):
        print(f"Requirements file not found: {req_file}")
        sys.exit(1)
    # Read requirements, ignoring comments and empty lines
    with open(req_file, "r") as f:
        requirements = [
            line.strip() for line in f if line.strip() and not line.startswith("#")
        ]

    total = len(requirements)
    if total == 0:
        print("No requirements to install.")
        return

    print("Installing prerequisites:")
    for idx, package in enumerate(requirements, start=1):
        # Calculate and display progress bar (50-char width)
        progress = int((idx / total) * 50)
        bar = "[" + "=" * progress + " " * (50 - progress) + "]"
        percent = (idx / total) * 100
        print(f"\r{bar} {percent:5.1f}% - Installing {package}...", end="", flush=True)
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        except subprocess.CalledProcessError:
            print(f"\nFailed to install {package}. Exiting.")
            sys.exit(1)
        time.sleep(0.1)  # Slight delay for visibility of progress update
    print("\nAll prerequisites installed successfully.")


if __name__ == "__main__":
    install_requirements()
