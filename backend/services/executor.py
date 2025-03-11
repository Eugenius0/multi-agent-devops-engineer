import subprocess
from pathlib import Path
import sys
import time

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = BASE_DIR / "automation_scripts"

MAX_EXECUTION_TIME = 1000  # ⏳ Set execution time limit

def run_script(script_name, repo_name, user_input):
    """Runs an automation script and streams its output, stopping after 100 seconds."""
    script_path = SCRIPTS_DIR / script_name

    if not script_path.exists():
        yield f"Error: Script {script_name} not found at {script_path}"
        return

    start_time = time.time()  # Track execution start time

    process = subprocess.Popen(
        ["python", "-u", str(script_path), repo_name, user_input], 
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True
    )

    # Stream standard output in real-time
    for line in iter(process.stdout.readline, ''):
        elapsed_time = time.time() - start_time
        if elapsed_time > MAX_EXECUTION_TIME:
            process.terminate()  # 🛑 Kill process if it exceeds 100 seconds
            yield "ERROR: ❌ Execution stopped: Runtime Error."
            return

        sys.stdout.write(line)
        sys.stdout.flush()  # 🔄 Force immediate output
        yield line  # 🔥 Stream line to FastAPI

    # Stream errors separately in real-time
    for err_line in iter(process.stderr.readline, ''):
        sys.stderr.write(err_line)
        sys.stderr.flush()
        yield f"ERROR: {err_line}"

    process.stdout.close()
    process.stderr.close()
    process.wait()
