import logging
import os
import subprocess
import sys
import webbrowser
import git
import re

from utils.utils import MODEL_NAME, clone_repo, get_github_username, run_command

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
            logging.error(f"\n❌ Errors (if any):\n {err}")
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
def generate_docker_files(user_input):
    """Generates Docker-related files dynamically based on the repo contents."""
    print("🤖 Generating Docker-related files with DeepSeek Coder v2 via Ollama...")

    prompts = {
        "Dockerfile.dev": f"""
        Generate a valid **Dockerfile.dev** for a React app.
        
        - Use Node.js 20 Alpine.
        - Set `WORKDIR /app`
        - Copy `package.json` and `package-lock.json` first.
        - Run `npm install`
        - Copy the rest of the files.
        - Start the development server with `npm start`.

        The output must be **raw and valid**, with **no explanations or Markdown formatting**.

        **User Request:**
        {user_input}
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
          - Exclude `node_modules/` from being overwritten (`- /app/node_modules`)
          - Expose port `3001:3000`
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
    print("✅ Pushed containerization files to GitHub!\n")

# Build and Run Containers
def build_and_run_containers():
    """Builds and runs Docker containers using docker-compose while filtering logs."""
    print("🚀 Building and running Docker containers...")

    # Run react-dev container but filter out unnecessary logs
    result_dev = run_command("docker-compose up react-dev -d", capture_output=True)
    for line in result_dev[1].split("\n"):  # Process stdout
        if not any(ignore in line for ignore in ["Created", "Starting", "Started"]):
            print(line.strip())

    # Run react-prod container but filter out unnecessary logs
    result_prod = run_command("docker-compose up react-prod -d", capture_output=True)
    for line in result_prod[1].split("\n"):  # Process stdout
        if not any(ignore in line for ignore in ["Created", "Starting", "Started"]):
            print(line.strip())


# Push to Docker Hub (Optional)
def push_to_docker_hub(username):
    """Tags and pushes the production image to Docker Hub."""
    username = username.lower()
    print("🚀 Pushing production image to Docker Hub...\n")
    tag_command = f"docker tag react-docker-app-react-prod {username}/react-docker-app"
    push_command = f"docker push {username}/react-docker-app"

    # Execute Docker Tagging
    run_command(tag_command, capture_output=False)

    # Execute Docker Push and filter the output
    result = subprocess.run(push_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Extract only the final digest and summary
    for line in result.stdout.split("\n"):
        if "digest:" in line:  # ✅ Only keep the final summary line
            print("✅ Docker Image Pushed\n")

    if result.returncode != 0:
        print(f"❌ Error pushing image: {result.stderr.strip()}")

def open_relevant_page(repo_name, docker_hub_user=None):
    """Automatically opens the most relevant URL after automation."""
    github_user = get_github_username()  # Retrieve dynamically

    # Default: Open the GitHub repository
    github_repo_url = f"https://github.com/{github_user}/{repo_name}"

    # If the app is running locally via docker-compose, open the local dev server
    if docker_hub_user:
        docker_hub_url = "https://hub.docker.com"
        print(f"\n🔗 Opening Docker Hub Repository: {docker_hub_url}")
        webbrowser.open(docker_hub_url)
    else:
        print(f"\n🔗 Opening GitHub Repository: {github_repo_url}")
        webbrowser.open(github_repo_url)

    # Check if containers are running and open the correct URL
    check_running = subprocess.run(["docker", "ps"], capture_output=True, text=True)
    
    if "react-dev" in check_running.stdout:
        print("\n🚀 Detected running React app in development mode. Opening browser...")
        webbrowser.open("http://localhost:3001")  # Open local dev server
    if "react-prod" in check_running.stdout:
        print("\n🚀 Detected running React app in production mode. Opening browser...\n")
        webbrowser.open("http://localhost:80")  # Open local production site

# 🔹 Main Automation Workflow
def main():
    print("🚀 Automating React app containerization with DeepSeek Coder v2 via Ollama...\n")

    # Get the GitHub repository name from the user
    repo_name = sys.argv[1]
    user_input = sys.argv[2]

    print(f"📂 Processing repository: {repo_name}\n")
    
    print("🚀 Cloning repository...\n")
    clone_repo(repo_name, platform="github", change_dir=True)

    # Analyze project
    if analyze_project() != "React":
        return

    # Generate Docker files dynamically
    generate_docker_files(user_input)

    # Commit and push to GitHub
    print("\n🔄 Committing and pushing workflow...\n")
    commit_and_push_files()

    # Build and run the containerized app
    build_and_run_containers()

    # Push the production image to Docker Hub
    # docker_hub_user = input("Enter your Docker Hub username (or press Enter to skip push): ")
    push_to_docker_hub("Eugenius00") # hardcoded for now

    print(f"🎉 Automation complete! React app containerized successfully from {repo_name}")

    # 🔗 Open the relevant page in the browser
    open_relevant_page(repo_name, "Eugenius00")

if __name__ == "__main__":
    main()

