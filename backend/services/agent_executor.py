from backend.services.state import approval_channels, cancelled_tasks
import subprocess
import os

def cancel_execution():
    """Cancel all pending approval tasks."""
    cancelled_tasks.update(approval_channels.keys())

def extract_action(content: str) -> str:
    """
    Extracts the first shell command from a string that includes 'Action:'.
    """
    for line in content.splitlines():
        if line.strip().lower().startswith("action:"):
            return line.split(":", 1)[1].strip()
    return ""

def execute_action(command: str, repo_name: str) -> str:
    """
    Executes a given shell command, using the current directory unless the
    command is a git clone (which should define its own target).
    """
    command = command.strip()

    # Identify if this is a clone operation
    is_clone = command.startswith("git clone")

    # Decide where to execute the command
    cwd = os.getcwd()  # Default to current dir

    # For non-clone commands, ensure the target repo folder exists
    if not is_clone:
        repo_path = os.path.join(cwd, repo_name)
        if not os.path.exists(repo_path):
            return f"❌ Error: Repository '{repo_name}' does not exist locally. Please clone it first."
        cwd = repo_path

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, cwd=cwd
        )

        if result.returncode == 0:
            return result.stdout.strip() or f"✅ Successfully executed: {command}"
        else:
            return f"❌ Command failed with error:\n{result.stderr.strip()}"

    except Exception as e:
        return f"❌ Exception while executing command:\n{str(e)}"
