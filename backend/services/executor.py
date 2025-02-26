import subprocess
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = BASE_DIR / "automation_scripts"

def run_script(script_name, repo_name):
    """Runs an automation script and passes the repo name as an argument."""
    script_path = SCRIPTS_DIR / script_name

    if not script_path.exists():
        return f"Error: Script {script_name} not found at {script_path}"

    try:
        process = subprocess.Popen(
            ["python", str(script_path), repo_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        stdout, stderr = process.communicate()
        return stdout if stdout else stderr
    except Exception as e:
        return f"Error executing script {script_name}: {str(e)}"
