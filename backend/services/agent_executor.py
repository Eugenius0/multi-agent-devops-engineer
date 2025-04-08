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

    # Check if the command includes 'git clone'
    is_clone = "git clone" in command

    # Compute working directory
    repo_path = os.path.join(base_dir, repo_name)
    cwd = base_dir if is_clone else repo_path

    # 💥 If it's NOT a clone command and repo doesn't exist locally, return early
    if not is_clone and not os.path.exists(repo_path):
        return f"❌ Error: Repository '{repo_name}' does not exist locally. Please clone it first."

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, cwd=cwd
        )
        if result.returncode == 0:
            return result.stdout.strip() or f"✅ Successfully executed: {command}"
        else:
            return f"❌ Command failed with error:\n{result.stderr.strip()}"
    except Exception as e:
        return f"❌ Exception: {str(e)}"