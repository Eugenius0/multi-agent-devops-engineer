import logging
import os
import subprocess
import sys
import git
import re

from utils.utils import MODEL_NAME, clone_repo

def setup_ci_dir(repo_name):
    """Ensures the GitLab pipeline configuration is in place."""
    os.makedirs(f"{repo_name}/.gitlab-ci", exist_ok=True)

def validate_yaml(repo_name):
    """Runs a basic syntax check for GitLab CI YAML files."""
    yaml_file = f"{repo_name}/.gitlab-ci.yml"
    if not os.path.exists(yaml_file):
        return False, "❌ YAML file not found."

    with open(yaml_file, "r") as file:
        content = file.read()
    
    if "stages" not in content or "script" not in content:
        return False, "❌ YAML file is missing required keys."

    return True, None

def extract_yaml(text):
    """Extracts only the first valid YAML block from LLM output."""
    yaml_blocks = re.findall(r"```yaml(.*?)```", text, re.DOTALL)

    if yaml_blocks:
        yaml_text = yaml_blocks[0].strip()
    else:
        yaml_text = text.strip()

    return yaml_text.replace("\t", "    ")  # Ensure YAML compliance

def generate_gitlab_ci(repo_name, user_input, attempt=1, last_error=None, last_yaml=""):
    """Generates a valid `.gitlab-ci.yml` using DeepSeek Coder via Ollama."""

    MAX_RETRIES = 3
    if attempt > MAX_RETRIES:
        logging.error("❌ Max retries reached. Using last valid YAML.")
        return last_yaml

    repo_path = f"./{repo_name}"
    files = os.listdir(repo_path)
    error_context = f"\n**Previous YAML attempt error:** {last_error}\n" if last_error else ""

    if attempt == 1:
        prompt = f"""
    You are an AI assistant generating a **strictly valid GitLab CI/CD pipeline**.

    **Rules:**
    - Your response **must be valid YAML** (no explanations or markdown).
    - Ensure the output **strictly follows GitLab CI/CD YAML format**.
    - **MANDATORY KEYS:** `stages`, `jobs`, and `script` must exist.
    - **Use `image: python:3.10` as the default environment.**
    - To know what exactly to generate, analyze the given repository contents {files} and consider the "User Request: {user_input}".
    - **For Python projects, install dependencies from `requirements.txt` before running tests.**
    - **Each job must contain `script:` with valid shell commands.**
    - **Use `needs:` to define job dependencies correctly.**
    
    **Generate ONE valid `.gitlab-ci.yml` below:**
    ```yaml
    """
    else:
        prompt = f"""
        We got this error message:{error_context}. Please fix it and generate the YAML again.
        """

    cmd = ["ollama", "run", MODEL_NAME]

    logging.info(f"🧠 Running Ollama to generate pipeline (Attempt {attempt}/{MAX_RETRIES})...\n")

    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        process.stdin.write(prompt)
        process.stdin.close()

        llm_output = ""
        for line in iter(process.stdout.readline, ""):
            logging.info(line, end="")
            llm_output += line

        process.stdout.close()
        return_code = process.wait()

        if return_code != 0:
            err = process.stderr.read()
            logging.error(f"\n❌ Errors (if any):\n {err}")
            process.stderr.close()

        yaml_output = extract_yaml(llm_output)
        logging.info("\n📝 **EXTRACTED YAML:**\n")
        logging.info(yaml_output)

        save_pipeline(repo_name, yaml_output)

        is_valid, error_message = validate_yaml(repo_name)

        if not is_valid:
            logging.error(f"⚠️ YAML Validation Failed! Error: {error_message}")
            return generate_gitlab_ci(repo_name, user_input, attempt=attempt + 1, last_error=error_message, last_yaml=yaml_output)

        logging.info(f"✅ Successfully generated valid YAML on attempt {attempt}")
        return yaml_output

    except Exception as e:
        logging.error(f"❌ Unexpected error: {e}")
        return last_yaml

def save_pipeline(repo_name, pipeline_content):
    """Saves the generated `.gitlab-ci.yml` file."""
    pipeline_file = f"{repo_name}/.gitlab-ci.yml"
    with open(pipeline_file, "w") as file:
        file.write(pipeline_content)

def commit_and_push_pipeline(repo_name):
    """Commits and pushes the GitLab CI/CD pipeline to the repository."""
    repo_path = os.path.join(os.getcwd(), repo_name)

    if not os.path.isdir(os.path.join(repo_path, ".git")):
        raise git.exc.InvalidGitRepositoryError(f"❌ {repo_path} is not a valid Git repository.")

    repo = git.Repo(repo_path)
    repo.git.add(update=True)
    repo.index.add([".gitlab-ci.yml"])
    repo.index.commit("Added GitLab CI/CD pipeline")
    repo.remote(name="origin").push()

if __name__ == "__main__":
    print("🚀 Automating GitLab CI/CD pipeline creation with DeepSeek Coder via Ollama...")
    
    repo_name = sys.argv[1]
    user_input = sys.argv[2]

    print(f"📂 Processing repository: {repo_name}")

    print("\n🚀 Cloning repository...")
    clone_repo(repo_name, change_dir=False)

    print("\n📂 Setting up pipeline directory...")
    setup_ci_dir(repo_name)

    print("\n🧠 Generating pipeline using DeepSeek Coder v2 on Ollama...")
    pipeline_yaml = generate_gitlab_ci(repo_name, user_input)
    save_pipeline(repo_name, pipeline_yaml)

    print("\n🔄 Committing and pushing pipeline...")
    commit_and_push_pipeline(repo_name)

    print("\n✅ GitLab CI/CD pipeline setup completed!")
