import logging
import os
import subprocess
import sys
import git

from utils.utils import MODEL_NAME, clone_repo, get_github_username

logging.basicConfig(level=logging.INFO)

PULUMI_PROJECT_NAME = "aws-react-deploy"
PULUMI_DIR_NAME = "pulumi"

def create_pulumi_folder(repo_name):
    """Create the Pulumi project folder inside the cloned repo."""
    pulumi_path = os.path.join(repo_name, PULUMI_DIR_NAME)
    os.makedirs(pulumi_path, exist_ok=True)
    logging.info(f"✅ Created Pulumi directory: {pulumi_path}")
    return pulumi_path

def write_file(path, content):
    """Utility to write content to a file."""
    with open(path, "w") as f:
        f.write(content)
    logging.info(f"✅ Created file: {path}")

def generate_pulumi_files(repo_name, user_name):
    """Generate Pulumi files inside the repo."""
    pulumi_path = create_pulumi_folder(repo_name)

    # 1. Pulumi.yaml
    pulumi_yaml = f"""
name: {PULUMI_PROJECT_NAME}
runtime: python
description: Deploys a React app to AWS EC2 using Pulumi
"""
    write_file(os.path.join(pulumi_path, "Pulumi.yaml"), pulumi_yaml.strip())

    # 2. requirements.txt
    requirements = "pulumi\npulumi-aws"
    write_file(os.path.join(pulumi_path, "requirements.txt"), requirements)

    # 3. __main__.py
    main_py = f'''
import pulumi
import pulumi_aws as aws

sec_group = aws.ec2.SecurityGroup("web-sec-group",
    description="Allow HTTP and SSH",
    ingress=[
        {{"protocol": "tcp", "from_port": 22, "to_port": 22, "cidr_blocks": ["0.0.0.0/0"]}},
        {{"protocol": "tcp", "from_port": 80, "to_port": 80, "cidr_blocks": ["0.0.0.0/0"]}},
    ])

instance = aws.ec2.Instance("react-app-server",
    ami="ami-0c55b159cbfafe1f0",
    instance_type="t2.micro",
    vpc_security_group_ids=[sec_group.id],
    key_name="your-key-pair",
    user_data=\"\"\"#!/bin/bash
    sudo yum update -y
    sudo yum install -y git nodejs npm
    cd /home/ec2-user
    git clone https://github.com/{user_name}/{repo_name}.git
    cd {repo_name}
    npm install
    npm start &
    \"\"\",
)

pulumi.export("instance_ip", instance.public_ip)
'''
    write_file(os.path.join(pulumi_path, "__main__.py"), main_py.strip())

def commit_pulumi_project(repo_name):
    """Add and commit the Pulumi project into the repo."""
    repo_path = os.path.join(os.getcwd(), repo_name)
    if not os.path.isdir(os.path.join(repo_path, ".git")):
        raise git.exc.InvalidGitRepositoryError(f"{repo_path} is not a valid Git repository.")

    repo = git.Repo(repo_path)
    repo.git.add(update=True)
    repo.index.add([f"{PULUMI_DIR_NAME}/Pulumi.yaml", f"{PULUMI_DIR_NAME}/__main__.py", f"{PULUMI_DIR_NAME}/requirements.txt"])
    repo.index.commit("🛠 Added Pulumi project for AWS EC2 deployment")
    repo.remote(name="origin").push()
    print("✅ Pushed Pulumi files to GitHub.")

def main():
    if len(sys.argv) < 3:
        print("Usage: python deploy_to_aws.py <repo_name> <user_input>")
        return

    repo_name = sys.argv[1]
    user_input = sys.argv[2]

    print(f"📦 Repo: {repo_name}")
    print(f"💬 User Request: {user_input}\n")

    # Clone the repo
    clone_repo(repo_name, platform="github", change_dir=False)

    user_name = get_github_username()

    print("\n🚧 Generating Pulumi files for AWS EC2 deployment...")
    generate_pulumi_files(repo_name, user_name)

    print("\n🔄 Committing Pulumi files to GitHub...")
    commit_pulumi_project(repo_name)

    print("\n🎉 Pulumi project added! To deploy manually:")
    print(f"cd {repo_name}/{PULUMI_DIR_NAME}")
    print("python3 -m venv venv && source venv/bin/activate")
    print("pip install -r requirements.txt")
    print("pulumi login --local")
    print("pulumi stack init dev")
    print("pulumi up")

if __name__ == "__main__":
    main()
