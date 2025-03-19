import logging
import os
import subprocess
import sys
import webbrowser
import git
import re

from utils.utils import MODEL_NAME, clone_repo, get_github_username, run_command

def setup_kubernetes_dir(repo_name):
    """Creates the k8s/ directory inside the repo."""
    os.makedirs(f"{repo_name}/k8s", exist_ok=True)
    logging.info(f"✅ Ensured Kubernetes directory: {repo_name}/k8s")

def extract_yaml(text):
    """Extracts only the first valid YAML block from LLM output."""
    yaml_blocks = re.findall(r"```yaml(.*?)```", text, re.DOTALL)
    return yaml_blocks[0].strip() if yaml_blocks else text.strip()

def generate_kubernetes_yaml(repo_name, user_input, filename, attempt=1, last_yaml=""):
    """Generates a valid Kubernetes YAML file using LLM with retries."""
    MAX_RETRIES = 3
    if attempt > MAX_RETRIES:
        logging.error("❌ Max retries reached. Using last valid YAML.")
        return last_yaml  

    repo_path = f"./{repo_name}"
    files = os.listdir(repo_path)

    prompt = f"""
    You are an AI assistant generating a **strictly valid Kubernetes YAML file**.

    **Rules:**
    - Your response **must be valid YAML** (no explanations or markdown).
    - Ensure the output **strictly follows Kubernetes YAML syntax**.
    - The filename must match `{filename}`.
    - To know what to generate, analyze the repository contents: {files}
    - Consider the "User Request: {user_input}".

    **Generate ONE valid `{filename}` below:**
    ```yaml
    """

    cmd = ["ollama", "run", MODEL_NAME]

    logging.info(f"🧠 Running LLM to generate {filename} (Attempt {attempt}/{MAX_RETRIES})...")

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
            logging.info(line.strip())  
            llm_output += line  

        process.stdout.close()
        return_code = process.wait()

        if return_code != 0:
            error_message = process.stderr.read().strip()
            logging.error(f"❌ Error: {error_message}")
            return generate_kubernetes_yaml(repo_name, user_input, filename, attempt + 1, last_yaml)

        yaml_output = extract_yaml(llm_output)
        save_yaml(repo_name, filename, yaml_output)
        return yaml_output

    except Exception as e:
        logging.error(f"❌ Unexpected error: {str(e)}")
        return last_yaml

def save_yaml(repo_name, filename, content):
    """Saves the generated Kubernetes YAML file inside k8s/ directory."""
    yaml_path = os.path.join(repo_name, "k8s", filename)
    with open(yaml_path, "w") as f:
        f.write(content)
    logging.info(f"✅ Saved {yaml_path}")

def commit_and_push_k8s_files(repo_name):
    """Commits and pushes Kubernetes YAML files to the repository."""
    repo_path = os.path.join(os.getcwd(), repo_name)
    k8s_dir = os.path.join(repo_path, "k8s")

    if not os.path.isdir(os.path.join(repo_path, ".git")):
        logging.warning("⚠️ Repository not found. Cloning...")
        clone_repo(repo_name, platform="github", change_dir=False)

    repo = git.Repo(repo_path)

    if not os.path.exists(k8s_dir) or not os.listdir(k8s_dir):
        logging.error(f"❌ No Kubernetes YAML files to commit in {k8s_dir}")
        return

    print("\n🚀 Committing Kubernetes manifests to GitHub...")
    repo.git.add(update=True)
    repo.index.add([os.path.join("k8s", f) for f in os.listdir(k8s_dir) if f.endswith(".yaml")])
    repo.index.commit("Added Kubernetes deployment and service YAML files")

    try:
        repo.remote(name="origin").push()
        print("\n✅ Kubernetes manifests pushed to GitHub.")
    except git.exc.GitCommandError as e:
        logging.error(f"❌ Git push failed: {str(e)}")

def build_and_push_docker_images(repo_name):
    """Builds and pushes Docker images to Docker Hub."""
    print("\n🚀 Building and pushing Docker images...")
    run_command(f"cd {repo_name}/backend && docker build -t my-backend-image .")
    run_command("docker tag my-backend-image eugenius00/my-backend-image")
    run_command("docker push eugenius00/my-backend-image")

    run_command(f"cd {repo_name}/frontend && npm install && npm run build")
    run_command(f"cd {repo_name}/frontend && docker build -t my-frontend-image .")
    run_command("docker tag my-frontend-image eugenius00/my-frontend-image")
    run_command("docker push eugenius00/my-frontend-image")

    logging.info("✅ Docker images built and pushed.")

def start_minikube():
    """Checks if Minikube is installed, installs it if missing, and starts it quickly."""
    
    # ✅ Check if Minikube is installed
    return_code, _, _ = run_command("minikube version", capture_output=True)
    
    if return_code != 0:
        logging.info("🚀 Minikube is not installed. Installing now...")
        run_command("brew install minikube", capture_output=True)
    else:
        logging.info("✅ Minikube is already installed.")
    
    # ✅ Start Minikube in fast mode (disables unnecessary checks)
    logging.info("🚀 Starting Minikube in fast mode...")
    run_command("minikube start --memory=4096 --cpus=2 --disk-size=10g --driver=docker --alsologtostderr", capture_output=True)
    logging.info("✅ Minikube started quickly.")


def deploy_to_kubernetes(repo_name):
    """Deploys the application to Kubernetes."""
    print("\n🚀 Deploying application to Kubernetes...")
    
    yaml_files = [
        "mongodb-deployment.yaml", "mongodb-service.yaml",
        "backend-deployment.yaml", "backend-service.yaml",
        "frontend-deployment.yaml", "frontend-service.yaml"
    ]

    for yaml_file in yaml_files:
        run_command(f"kubectl apply -f {repo_name}/k8s/{yaml_file}")

    logging.info("✅ Deployment completed.")

def scale_backend():
    """Scales the backend deployment."""
    print("\n🚀 Scaling backend to 3 replicas...")
    run_command("kubectl scale deployment backend --replicas=3")
    logging.info("✅ Backend scaled.")

import subprocess

def get_frontend_url():
    """Runs the Minikube command to get the frontend service URL and prints its output without getting stuck."""
    logging.info("🚀 Fetching frontend service URL...")

    try:
        # ✅ Run Minikube command synchronously
        return_code, output, stderr = run_command("minikube service frontend-service --url", capture_output=True)

        if return_code == 0 and output:
            logging.info(f"✅ Minikube Output: {output}")
            print(f"\n🎉 Minikube Output:\n{output}\n")
            return output  # Return the raw output
        else:
            logging.error(f"❌ Minikube command failed: {stderr}")
            print("❌ Minikube command failed. Check if Minikube and the service are running.")
            return None
    except Exception as e:
        logging.error(f"❌ Unexpected error in get_frontend_url: {e}")
        return None


if __name__ == "__main__":
    print("🚀 Automating Kubernetes deployment with DeepSeek Coder v2 via Ollama...\n")

    repo_name = sys.argv[1]
    user_input = sys.argv[2]

    print(f"📂 Processing repository: {repo_name}")

    print("\n🚀 Cloning repository...")
    clone_repo(repo_name, platform="github", change_dir=False)

    print("\n📂 Setting up Kubernetes directory...")
    setup_kubernetes_dir(repo_name)

    print("\n🧠 Generating Kubernetes YAML files...")
    yaml_files = [
        "mongodb-deployment.yaml", "mongodb-service.yaml",
        "backend-deployment.yaml", "backend-service.yaml",
        "frontend-deployment.yaml", "frontend-service.yaml"
    ]

    for yaml_file in yaml_files:
        generate_kubernetes_yaml(repo_name, user_input, yaml_file)

    print("\n🔄 Committing and pushing Kubernetes manifests...")
    commit_and_push_k8s_files(repo_name)

    print("\n🚀 Building and pushing Docker images...")
    build_and_push_docker_images(repo_name)

    print("\n🚀 Starting Minikube...")
    start_minikube()

    print("\n🚀 Deploying to Kubernetes...")
    deploy_to_kubernetes(repo_name)

    print("\n🚀 Scaling backend...")
    scale_backend()

    print("\n🔗 Fetching frontend service URL...")
    get_frontend_url()

    print("\n✅ Kubernetes automation completed!")
