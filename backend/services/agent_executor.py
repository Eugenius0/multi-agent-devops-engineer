from backend.services.state import approval_channels, cancelled_tasks

def cancel_execution():
    cancelled_tasks.update(approval_channels.keys())

def extract_action(content: str) -> str:
    for line in content.splitlines():
        if line.strip().lower().startswith("action:"):
            return line.split(":", 1)[1].strip()
    return ""

import subprocess
import os

def execute_action(command: str, repo_name: str) -> str:
    base_dir = "./repos"
    os.makedirs(base_dir, exist_ok=True)

    is_clone = command.strip().startswith("git clone")
    cwd = base_dir if is_clone else os.path.join(base_dir, repo_name)

    if not is_clone and not os.path.exists(cwd):
        return f"❌ Error: Repository directory does not exist: {cwd}"

    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=cwd)
        if result.returncode == 0:
            return result.stdout.strip() or f"✅ Successfully executed: {command}"
        else:
            return f"❌ Command failed:\n{result.stderr.strip()}"
    except Exception as e:
        return f"❌ Exception: {str(e)}"

