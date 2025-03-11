import logging
import os
import subprocess


logging.basicConfig(format="%(asctime)s%(levelname)s:%(message)s", level=logging.ERROR)

def get_github_username():
    """Fetch the GitHub username from the global Git config."""
    try:
        result = subprocess.run(["git", "config", "--global", "user.name"], capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None
    
# GitHub Credentials
GITHUB_TOKEN = "your-github-token"
GITHUB_USER = get_github_username() or input("Enter your GitHub username: ").strip()

MODEL_NAME = "deepseek-coder-v2" # change to prefered model
    
def run_command(command, capture_output=True):
    """Executes a shell command with optional output capture."""
    try:
        if capture_output:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        else:
            subprocess.run(command, shell=True, check=True)
            logging.info(f"✅ Successfully executed: {command}")
            return 0, None, None  # Success with no captured output
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Error executing: {command}\n{e}")
        return e.returncode, None, str(e)  # Return error details

# Clone the GitHub Repository
def clone_repo(repo_name, change_dir=False):
    """Clones a GitHub repository if not already cloned.

    Args:
        repo_name (str): The name of the repository.
        change_dir (bool): Whether to change into the repo directory after cloning.
    """
    repo_path = os.path.join(os.getcwd(), repo_name)

    if os.path.isdir(repo_path) and os.path.isdir(os.path.join(repo_path, ".git")):
        logging.info(f"✅ Repository {repo_name} already exists locally. Skipping clone...")
    else:
        repo_url = f"https://github.com/{GITHUB_USER}/{repo_name}.git"
        print(f"🚀 Cloning repository from {repo_url} ...")
        return_code, _, stderr = run_command(f"git clone {repo_url}")

        if return_code != 0:
            raise RuntimeError(f"❌ Failed to clone repository: {stderr}")

    if change_dir:
        os.chdir(repo_name)  # Only change directory if specified

    return repo_name
