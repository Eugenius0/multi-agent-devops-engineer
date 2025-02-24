import subprocess
import os
from pathlib import Path

# Path to automation scripts
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "automation_scripts"

def run_script(script_name):
    """Runs an automation script and returns its output."""
    script_path = SCRIPTS_DIR / script_name

    if not script_path.exists():
        return f"Error: Script {script_name} not found."

    try:
        process = subprocess.Popen(
            ["python", str(script_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        stdout, stderr = process.communicate()
        return stdout if stdout else stderr
    except Exception as e:
        return f"Error executing script {script_name}: {str(e)}"
