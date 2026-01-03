import os
import sys
import re
import shutil
from pathlib import Path
from datetime import datetime
from gradio_client import Client
from gradio_client.utils import handle_file
# ----- Prevent multiple concurrent executions -----
import psutil

LOCK_FILE = "/root/speech2text/stream_onlineradio/transcribewave/tmp/transcription_script.lock"

def is_already_running():
    """Check if another instance of this script is already running."""
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                pid = int(f.read().strip())

            # Check if PID is still active
            if psutil.pid_exists(pid):
                print(f"Another instance is already running with PID {pid}. Exiting.")
                return True

        except Exception:
            # If error reading PID, overwrite the file
            pass

    # Write our PID into lock file
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

    return False


# Call the check
if is_already_running():
    sys.exit(0)
# ---------------------------------------------------


def main():
    print("Test")


if __name__ == "__main__":
    # Cleanup lock file when exiting
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except:
        pass

    sys.exit(main())
