import os
import subprocess
import re

# 👉 Set this to your GitHub username or load from .env/config
GITHUB_USER = "eugenius0"

MODEL_NAME = "deepseek-coder-v2"  # Change to preferred model

def run_shell_command(cmd):
    # Skip 'git clone' if already cloned
    if "git clone" in cmd and os.path.exists(".git"):
        yield "🛑 Skipping 'git clone' – repository already exists.\n"
        return

    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in iter(process.stdout.readline, ""):
        yield line
    process.stdout.close()
    process.wait()

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    return f"✅ File written: {path}"

def parse_action(output):
    output = output.strip()

    if "```file:" in output:
        match = re.search(r"```file:\s*(.*?)\n(.*?)```", output, re.DOTALL)
        return "file", (match.group(1).strip(), match.group(2).strip()) if match else ("", "")

    elif "```bash" in output:
        match = re.search(r"```bash\n(.*?)```", output, re.DOTALL)
        if match:
            commands = match.group(1).strip()
            return "commands", commands

    elif "```yaml" in output:
        match = re.search(r"```yaml\n(.*?)```", output, re.DOTALL)
        if match:
            return "file", (".github/workflows/generated.yml", match.group(1).strip())

    elif "```done" in output:
        return "done", None

    return "unknown", output

def get_repo_overview(path):
    result = []
    for root, dirs, files in os.walk(path):
        for file in files:
            rel = os.path.relpath(os.path.join(root, file), path)
            result.append(rel)
    return "\n".join(result)

def get_repo_metadata(repo_name):
    repo_dir = repo_name.split("/")[-1]
    local_path = os.path.join(os.getcwd(), repo_dir)
    is_cloned = os.path.isdir(local_path) and os.path.isdir(os.path.join(local_path, ".git"))
    return {
        "repo_name": repo_name,
        "repo_dir": repo_dir,
        "platform": "github",
        "is_cloned": is_cloned,
        "local_path": local_path,
        "repo_url": f"https://github.com/{GITHUB_USER}/{repo_dir}.git"
    }

def call_llm(prompt):
    import ollama
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}]
    )
    return response["message"]["content"]

def build_prompt(user_input, repo_name):
    meta = get_repo_metadata(repo_name)
    repo_tree = get_repo_overview(meta["local_path"]) if meta["is_cloned"] else "[Not cloned yet]"

    return f"""
You are an autonomous AI DevOps agent.

Your task is to figure out how to fulfill the user's request by reasoning step-by-step and executing actions as needed.

You MUST decide what to do at each step: clone the repo if needed, create files, run commands, etc.

🧠 USER REQUEST:
{user_input}

ℹ️ REPO METADATA:
- Repo Name: {meta['repo_name']}
- Local Dir: {meta['repo_dir']}
- Platform: {meta['platform']}
- Already Cloned: {"✅ Yes" if meta['is_cloned'] else "❌ No"}
- Repo URL: {meta['repo_url']}
- Current Working Directory: {os.getcwd()}

📁 Current Project Structure:
{repo_tree}

✅ RULES:
- DO NOT include explanations or markdown formatting.
- DO NOT include yaml or json.
- Use ONLY `bash` or `file:` blocks.
- Do NOT use placeholders like `<shell command>`.
- Do NOT repeat actions (like re-cloning).
- Do NOT use `cd` unless absolutely necessary (you’re likely already in the right folder).
- DO NOT use 'echo ... > file' to write files. Use ```file: blocks instead.
- When you are fully done, respond with:

```done
"""

def run_agent_loop(repo_name, user_input):
    prompt = build_prompt(user_input, repo_name)
    history = prompt

    for _ in range(1):  # Avoid infinite loops
        llm_output = call_llm(history)
        yield f"\n🧠 LLM Output:\n{llm_output}\n"

        action_type, payload = parse_action(llm_output)

        if action_type == "commands":
            yield from handle_commands(payload)
            history += f"\nResult:\nExecuted commands:\n{payload}\n"

        elif action_type == "file":
            result = handle_file(payload)
            yield result
            history += f"\nResult:\n{result}\n"

        elif action_type == "done":
            yield "\n🎉 Task complete!"
            break

        else:
            yield "\n⚠️ Couldn't understand LLM output. Stopping."
            break

def handle_commands(commands):
    for line in commands.split("\n"):
        line = line.strip()
        if not line:
            continue
        for output in run_shell_command(line):
            yield output

def handle_file(payload):
    path, content = payload
    return write_file(path, content)
