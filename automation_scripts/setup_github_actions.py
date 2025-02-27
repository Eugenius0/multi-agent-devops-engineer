import logging
import os
import subprocess
import sys
import git
import re

from utils.utils import MODEL_NAME, clone_repo, run_command

def setup_workflow_dir(repo_name):
    """Creates the .github/workflows directory inside the repo."""
    os.makedirs(f"{repo_name}/.github/workflows", exist_ok=True)

def validate_yaml(repo_name):
    """Runs GitHub Actions validation using `act` and streams the output."""
    logging.info("\n🔍 Running GitHub Actions validation with `act`...\n")
    
    process = subprocess.Popen(
        f"cd {repo_name} && act -n --container-architecture linux/amd64",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # 🔄 Stream output in real-time
    for line in iter(process.stdout.readline, ""):
        logging.info(line, end="")  # Print each line as it's received

    stdout_output, stderr_output = process.communicate()
    return_code = process.returncode

    if return_code != 0:
        error_message = stderr_output.strip() or stdout_output.strip()
        logging.error(f"\n❌ GitHub Actions validation failed:\n {error_message}")
        return False, error_message  # Return the actual validation error

    logging.info("\n✅ GitHub Actions workflow is valid!")
    return True, None



def extract_yaml(text):
    """Extracts only the first valid YAML block from LLM output."""
    yaml_blocks = re.findall(r"```yaml(.*?)```", text, re.DOTALL)

    if yaml_blocks:
        yaml_text = yaml_blocks[0].strip()
    else:
        yaml_text = text.strip()

    return yaml_text.replace("\t", "    ")  # Convert tabs to spaces for YAML compliance

def generate_workflow(repo_name, attempt=1, last_error=None, last_yaml=""):
    """Generates a GitHub Actions workflow YAML file using DeepSeek-R1 via Ollama.
       If invalid, retries automatically up to MAX_RETRIES.
    """

    MAX_RETRIES = 3  # ✅ Increase retry limit for better correction attempts

    if attempt > MAX_RETRIES:
        logging.debug("❌ Reached max retries. Keeping last generated YAML.")
        return last_yaml  # ✅ Return last valid YAML instead of error message

    repo_path = f"./{repo_name}"
    files = os.listdir(repo_path)

    error_context = f"\n**Previous YAML attempt had this error:** {last_error}\n" if last_error else ""

    if attempt == 1:
        prompt = f"""
    You are an AI assistant generating a **strictly valid GitHub Actions workflow**.

    **Rules:**
    - Your response **must be valid YAML** (no explanations or markdown).
    - Ensure the output **strictly follows GitHub Actions YAML format**.
    - **MANDATORY KEYS:** `name`, `on`, and `jobs` **must** exist in the output.
    - **Trigger the workflow with `on:` (e.g., `push:` or `pull_request:`)**.
    - **Use `runs-on: ubuntu-latest` for each job**.
    - **Each job must contain `steps:` using `uses:` or `run:` correctly**.
    - **The workflow must contain two jobs: `build` and `test`.**
    - **The `test` job must run after `build` using `needs: build`**.
    - **The `test` job must run the correct test command based on the repository contents.**

    **Repository Contents:**
    {files}

    **Generate ONE valid GitHub Actions workflow below:**
    ```yaml
    """
    else:
        prompt = f"""
        We got this error message:{error_context}. Please try to fix it and try again. 
        """

    cmd = ["ollama", "run", MODEL_NAME]

    logging.info(f"🧠 Running Ollama to generate workflow (Attempt {attempt}/{MAX_RETRIES})...\n")

    try:
        # Open the subprocess with a pipe for streaming output
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffering for real-time output
            universal_newlines=True
        )

        # Send the prompt to Ollama
        process.stdin.write(prompt)
        process.stdin.close()

        # 🔥 Live Output Streaming: Print each line as it arrives
        logging.info("\n📜 **RAW OUTPUT FROM LLM:**\n")
        llm_output = ""
        for line in iter(process.stdout.readline, ""):
            logging.info(line, end="")  # Print each line as it's received
            llm_output += line  # Collect full output for processing

        process.stdout.close()
        return_code = process.wait()

        # Handle errors
        if return_code != 0:
            err = process.stderr.read()
            logging.error(f"\n❌ Errors (if any):\n {err}")
            process.stderr.close()

        # ✅ Extract only the YAML part
        yaml_output = extract_yaml(llm_output)

        # 🔥 DEBUG: Print extracted YAML before saving
        logging.info("\n📝 **EXTRACTED YAML:**\n")
        logging.info(yaml_output)

        # ✅ Save the extracted YAML (always save latest generated YAML)
        save_workflow(repo_name, yaml_output)

        # ✅ Validate YAML using `act` before pushing
        is_valid, error_message = validate_yaml(repo_name)

        if not is_valid:
            logging.error(f"⚠️ YAML Validation Failed! Error: {error_message}")
            logging.info("🔄 Retrying with updated prompt including the error...")
    
         # 🔄 Retry with the last generated YAML
            return generate_workflow(repo_name, attempt=attempt + 1, last_error=error_message, last_yaml=yaml_output)

        logging.info(f"✅ Successfully generated valid YAML on attempt {attempt}")
        return yaml_output  # ✅ Use valid YAML

    except Exception as e:
        logging.error(f"❌ Unexpected error: {e}")
        return last_yaml  # ✅ Return last known valid YAML to prevent breaking

def save_workflow(repo_name, workflow_content):
    """Saves the generated workflow YAML file inside .github/workflows."""
    workflow_file = f"{repo_name}/.github/workflows/github-actions-pipeline.yml"
    with open(workflow_file, "w") as file:
        file.write(workflow_content)

def commit_and_push_workflow(repo_name):
    """Commits and pushes the GitHub Actions workflow to the repository."""
    repo_path = os.path.join(os.getcwd(), repo_name)  # ✅ Ensure correct repo path

    if not os.path.isdir(os.path.join(repo_path, ".git")):
        raise git.exc.InvalidGitRepositoryError(f"❌ {repo_path} is not a valid Git repository.")

    repo = git.Repo(repo_path)  # ✅ Initialize the existing repository
    repo.git.add(update=True)
    repo.index.add([".github/workflows/github-actions-pipeline.yml"])
    repo.index.commit("Added GitHub Actions workflow")
    repo.remote(name="origin").push()

def install_github_cli():
    """Installs GitHub CLI if not present."""
    if run_command("gh --version", capture_output=True)[0] != 0:
        run_command("brew install gh", capture_output=True)

def authenticate_github():
    """Authenticates GitHub CLI."""
    if run_command("gh auth status", capture_output=True)[0] != 0:
        run_command("gh auth login", capture_output=True)

def trigger_workflow(repo_name):
    """Triggers the GitHub Actions workflow execution."""
    run_command(f"cd {repo_name} && gh workflow run github-actions-pipeline.yml", capture_output=True)

if __name__ == "__main__":
    print("🚀 Automating GitHub Actions pipeline creation with DeepSeek Coder v2 via Ollama...")
    
    repo_name = sys.argv[1]
    print(f"📂 Processing repository: {repo_name}")

    print("\n🚀 Cloning repository...")
    clone_repo(repo_name, change_dir=False)

    print("\n📂 Setting up workflow directory...")
    setup_workflow_dir(repo_name)

    print("\n🧠 Generating workflow using DeepSeek Coder v2 on Ollama...")
    workflow_yaml = generate_workflow(repo_name)
    save_workflow(repo_name, workflow_yaml)

    print("\n🔄 Committing and pushing workflow...")
    commit_and_push_workflow(repo_name)

    print("\n🛠 Ensuring GitHub CLI is installed...")
    install_github_cli()

    print("\n🔑 Authenticating GitHub CLI...")
    authenticate_github()

    print("\n🚀 Triggering GitHub Actions workflow...")
    trigger_workflow(repo_name)

    print("\n✅ GitHub Actions pipeline setup and execution completed!")
