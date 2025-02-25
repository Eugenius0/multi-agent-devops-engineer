import subprocess
import os
from pathlib import Path

# Get the absolute path of the project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = BASE_DIR / "automation_scripts"

def run_script(script_name):
    """Runs an automation script and returns its output."""
    script_path = SCRIPTS_DIR / script_name

    if not script_path.exists():
        return f"Error: Script {script_name} not found at {script_path}"

    try:
        process = subprocess.Popen(
            ["python", str(script_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        stdout, stderr = process.communicate()
        return stdout if stdout else stderr
    except Exception as e:
        return f"Error executing script {script_name}: {str(e)}"
