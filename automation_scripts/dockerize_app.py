import logging
import os
import subprocess
import sys
import git
import re

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

def run_command(command):
    """Executes a shell command and returns output."""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def execute_command(command):
    """Executes a shell command and prints the output."""
    try:
        subprocess.run(command, shell=True, check=True)
        logging.info(f"✅ Successfully executed: {command}")
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Error executing: {command}\n{e}")

def write_file(filename, content):
    """Writes generated content to a file."""
    with open(filename, "w") as f:
        f.write(content)
    logging.info(f"✅ {filename} created!")

def generate_with_ollama(prompt):
    """Calls DeepSeek Coder via Ollama in the terminal to generate file content."""
    
    # Ensure the model outputs ONLY valid code (no explanations)
    strict_prompt = f"""
    You are an AI assistant generating **strictly valid file contents**.
    
    **Rules:**
    - Your response **must ONLY contain valid code** (no explanations or markdown formatting).
    - Do **NOT** add any extra text before or after the code.
    - Output should be raw and usable as-is.

    **Task:**
    {prompt}

    **Only return the full file content below:**
    """
    
    cmd = ["ollama", "run", MODEL_NAME]

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

        process.stdin.write(strict_prompt)
        process.stdin.close()

        logging.info("\n📜 **RAW OUTPUT FROM LLM:**\n")
        llm_output = ""
        for line in iter(process.stdout.readline, ""):
            logging.info(line, end="")  # Print each line as it's received
            llm_output += line  # Collect full output for processing

        process.stdout.close()
        return_code = process.wait()

        if return_code != 0:
            err = process.stderr.read()
            logging.error("\n❌ Errors (if any):\n", err)
            process.stderr.close()

        # 🛠 Extract only the valid file content (strip unwanted markdown blocks)
        return extract_code(llm_output)

    except Exception as e:
        logging.error(f"❌ Error running Ollama: {e}")
        return ""

# 📌 Extract Only the Code Block from LLM Output
def extract_code(text):
    """Extracts the main code block from LLM output, removing explanations or markdown artifacts."""
    
    # Try to extract from a markdown code block (if present)
    code_blocks = re.findall(r"```(?:\w+)?\n(.*?)```", text, re.DOTALL)
    
    if code_blocks:
        code_text = code_blocks[0].strip()
    else:
        code_text = text.strip()  # Otherwise, return full text with whitespace trimmed

    return code_text.replace("\t", "    ")  # Ensure no tab issues for YAML compliance



# Clone the GitHub Repository
def clone_repo(repo_name):
    """Clones the given GitHub repository if not already cloned."""
    repo_path = os.path.join(os.getcwd(), repo_name)

    if os.path.isdir(repo_path) and os.path.isdir(os.path.join(repo_path, ".git")):
        logging.info(f"✅ Repository {repo_name} already exists locally. Skipping clone...")
    else:
        repo_url = f"https://github.com/{GITHUB_USER}/{repo_name}.git"
        print(f"🚀 Cloning repository from {repo_url} ...")
        return_code, _, stderr = run_command(f"git clone {repo_url}")

        if return_code != 0:
            raise RuntimeError(f"❌ Failed to clone repository: {stderr}")
        
    os.chdir(repo_name)
    return repo_name

# Analyze the Project Structure
def analyze_project():
    """Analyzes the project structure and detects if it's a React app."""
    if os.path.exists("package.json"):
        logging.info("🛠 Detected a JavaScript/Node.js project.")
        with open("package.json", "r") as f:
            package_json = f.read()
        if '"react"' in package_json:
            logging.info("✅ React app detected!")
            return "React"
    logging.error("❌ React app not detected. Exiting...")
    return None

# Generate Docker & Compose Files with DeepSeek Coder
def generate_docker_files():
    """Generates Docker-related files dynamically based on the repo contents."""
    print("🤖 Generating Docker-related files with DeepSeek Coder v2 via Ollama...")

    prompts = {
        "Dockerfile.dev": """
        Generate a valid **Dockerfile.dev** for a React app.
        
        - Use Node.js 20 Alpine.
        - Set `WORKDIR /app`
        - Copy `package.json` and `package-lock.json` first.
        - Run `npm install`
        - Copy the rest of the files.
        - Start the development server with `npm start`.

        The output must be **raw and valid**, with **no explanations or Markdown formatting**.
        """,
        
        "Dockerfile": """
        Generate a **production-ready** Dockerfile for a React app.
        
        - Use multi-stage builds.
        - Stage 1: Use `node:20-alpine` as the builder.
          - Set `WORKDIR /app`
          - Copy `package.json` and `package-lock.json`
          - Run `npm install`
          - Copy all files
          - Run `npm run build`
        - Stage 2: Use `nginx:stable-alpine` as the web server.
          - Copy built files from `/app/build` to `/usr/share/nginx/html`
          - Expose port `80`
          - Start Nginx.
        
        The output must be **raw and valid**, with **no explanations or Markdown formatting**.
        """,

        ".dockerignore": """
        Generate a `.dockerignore` file for a React app.
        
        - Ignore `node_modules/`
        - Ignore `.git/`
        - Ignore `.env`
        - Ignore `build/`
        - Ignore `Dockerfile`
        - Ignore `.gitignore`
        """,
        
        "docker-compose.yml": """
        Generate a **valid** `docker-compose.yml` for a React app.
        
        - Define two services: `react-dev` and `react-prod`.
        - `react-dev` should:
          - Build from `Dockerfile.dev`
          - Use `stdin_open: true` and `tty: true`
          - Mount volumes for live reloading (`./:/app`)
          - Expose port `3000`
        - `react-prod` should:
          - Build from `Dockerfile`
          - Expose port `80`
        
        The output must be **raw and valid**, with **no explanations or Markdown formatting**.
        """
    }

    for filename, prompt in prompts.items():
        content = generate_with_ollama(prompt)
        if content:
            write_file(filename, content)

# Commit and Push to GitHub
def commit_and_push_files():
    """Commits and pushes the generated Docker files to the GitHub repository."""
    repo_path = os.path.join(os.getcwd())  # Set correct path

    if not os.path.isdir(os.path.join(repo_path, ".git")):
        raise git.exc.InvalidGitRepositoryError(f"❌ {repo_path} is not a valid Git repository.")

    repo = git.Repo(repo_path)
    repo.git.add(update=True)
    repo.index.add(["Dockerfile.dev", "Dockerfile", ".dockerignore", "docker-compose.yml"])
    repo.index.commit("Added Docker containerization setup")
    repo.remote(name="origin").push()
    print("✅ Pushed containerization files to GitHub!")

# Build and Run Containers
def build_and_run_containers():
    """Builds and runs Docker containers using docker-compose."""
    print("🚀 Building and running Docker containers...")
    execute_command("docker-compose up react-dev -d")
    execute_command("docker-compose up react-prod -d")

# Push to Docker Hub (Optional)
def push_to_docker_hub(username):
    """Tags and pushes the production image to Docker Hub."""
    print("🚀 Pushing production image to Docker Hub...")
    tag_command = f"docker tag react-docker-app-react-prod {username}/react-docker-app"
    push_command = f"docker push {username}/react-docker-app"

    execute_command(tag_command)
    execute_command(push_command)

# 🔹 Main Automation Workflow
def main():
    print("🚀 Automating React app containerization with DeepSeek Coder v2 via Ollama...")

    # Get the GitHub repository name from the user
    repo_name = sys.argv[1]
    print(f"📂 Processing repository: {repo_name}")
    
    print("\n🚀 Cloning repository...")
    clone_repo(repo_name)

    # Analyze project
    if analyze_project() != "React":
        return

    # Generate Docker files dynamically
    generate_docker_files()

    # Commit and push to GitHub
    print("\n🔄 Committing and pushing workflow...")
    commit_and_push_files()

    # Build and run the containerized app
    build_and_run_containers()

    # Optional: Push the production image to Docker Hub
    docker_hub_user = input("Enter your Docker Hub username (or press Enter to skip push): ")
    if docker_hub_user:
        push_to_docker_hub(docker_hub_user)

    print(f"🎉 Automation complete! React app containerized successfully from {repo_name}")

if __name__ == "__main__":
    main()

