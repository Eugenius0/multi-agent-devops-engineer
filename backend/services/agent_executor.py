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
            return "commands", match.group(1).strip()

    elif "```yaml" in output:
        match = re.search(r"```yaml\n(.*?)```", output, re.DOTALL)
        if match:
            return "file", (".github/workflows/generated.yml", match.group(1).strip())

    elif "```done" in output:
        return "done", None

    # Fallback for raw shell commands (unwrapped)
    if re.match(r"^(git|npm|mkdir|touch|cd|rm|echo|python|bash)", output.strip(), re.IGNORECASE):
        return "commands", output.strip()

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
You are an autonomous AI DevOps engineer that plans and executes tasks step by step.

Your job is to fulfill the user's request by reasoning through each step (Thought), choosing the right action (Action), and observing the result (Result).

Each step MUST follow this format:

Thought: <reasoning>
Action:
```bash
<shell command>
OR:
Action:
<file content>
✅ **RULES:**

- DO NOT explain outside the `Thought:` section.
- DO NOT use markdown formatting like `yaml` or `json`.
- DO NOT include placeholders like `<shell command>`.
- Use **ONLY** `bash` or `file:` blocks for `Action`.
- DO NOT repeat previous actions.
- Use `file:` blocks instead of `echo > filename`.
- When all required steps are done, respond with:

User Request: {user_input}
Repository structure: {repo_tree}"""

def run_agent_loop(repo_name, user_input):
    prompt = build_prompt(user_input, repo_name)
    history = prompt
    executed_steps = set()
    for _ in range(10):  # Limit to avoid infinite loops
        llm_output = call_llm(history)
        yield f"\n🧠 LLM Output:\n{llm_output}\n"

        action_type, payload = parse_action(llm_output)

        # Prevent duplicate actions
        if action_type in ["commands", "file"] and payload in executed_steps:
            yield "\n⏩ Skipping repeated action.\n"
            continue
        executed_steps.add(payload)

        if action_type == "commands":
            result_output = ""
            for output in handle_commands(payload):
                yield output
                result_output += output
            history += f"\n{llm_output}\nResult:\n{result_output.strip()}\n"

        elif action_type == "file":
            result = handle_file(payload)
            yield result
            history += f"\n{llm_output}\nResult:\n{result.strip()}\n"

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