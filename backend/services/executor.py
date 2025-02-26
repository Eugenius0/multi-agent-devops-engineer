import subprocess
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = BASE_DIR / "automation_scripts"

def run_script(script_name, repo_name):
    """Runs an automation script and streams its output."""
    script_path = SCRIPTS_DIR / script_name

    if not script_path.exists():
        yield f"Error: Script {script_name} not found at {script_path}"
        return

    process = subprocess.Popen(
        ["python", str(script_path), repo_name], 
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True
    )

    for line in iter(process.stdout.readline, ""):
        yield line.strip()  # Stream standard output
    
    for err_line in iter(process.stderr.readline, ""):
        yield f"ERROR: {err_line.strip()}"  # Stream error messages

    process.stdout.close()
    process.stderr.close()
    process.wait()
