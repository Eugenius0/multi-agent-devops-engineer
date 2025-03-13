import subprocess
from pathlib import Path
import sys
import time

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = BASE_DIR / "automation_scripts"

MAX_EXECUTION_TIME = 1000  # ⏳ Set execution time limit

running_process = None  # 🔹 Store the running subprocess globally
stop_execution = False  # 🔹 Global flag for cancellation

def run_script(script_name, repo_name, user_input):
    """Runs an automation script and stops immediately when cancelled."""
    global stop_execution
    stop_execution = False  # Reset cancellation flag at the start

    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        yield f"Error: Script {script_name} not found at {script_path}"
        return

    start_time = time.time()  # Track execution start time

    process = subprocess.Popen(
        ["python", "-u", str(script_path), repo_name, user_input], 
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True
    )

    global running_process
    running_process = process  # Store the active process

    for line in iter(process.stdout.readline, ''):
        if stop_execution:  # If user cancels, terminate immediately
            process.terminate()
            yield "ERROR: ❌ Execution Cancelled by User."
            return

        elapsed_time = time.time() - start_time
        if elapsed_time > MAX_EXECUTION_TIME:
            process.terminate()
            yield "ERROR: ❌ Execution stopped: Runtime Error."
            return

        sys.stdout.write(line)
        sys.stdout.flush()  
        yield line  

    # Stream errors separately
    for err_line in iter(process.stderr.readline, ''):
        if stop_execution:
            process.terminate()
            yield "ERROR: ❌ Execution Cancelled by User."
            return

        sys.stderr.write(err_line)
        sys.stderr.flush()
        yield f"ERROR: {err_line}"

    process.stdout.close()
    process.stderr.close()
    process.wait()


def cancel_execution():
    """Stops the running process and prevents further Git operations."""
    global stop_execution
    stop_execution = True

    if running_process:
        running_process.terminate()
