# services/agent_executor.py
import os
import subprocess
import re

def run_shell_command(cmd):
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
    if "```bash" in output:
        match = re.search(r"```bash\n(.*?)```", output, re.DOTALL)
        return "command", match.group(1) if match else ""
    elif "```file:" in output:
        match = re.search(r"```file:\s*(.*?)\n(.*?)```", output, re.DOTALL)
        return "file", (match.group(1).strip(), match.group(2)) if match else ("", "")
    elif "```done" in output:
        return "done", None
    return "unknown", output

def get_repo_overview(repo_name):
    result = []
    for root, dirs, files in os.walk(repo_name):
        for file in files:
            rel = os.path.relpath(os.path.join(root, file), repo_name)
            result.append(rel)
    return "\n".join(result)

MODEL_NAME = "deepseek-coder-v2" # change to prefered model

def call_llm(prompt):
    import ollama
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}]
    )
    return response["message"]["content"]

def build_prompt(user_input, repo_name):
    repo_tree = get_repo_overview(repo_name)
    return f"""
You are an AI DevOps agent that can write files or execute shell commands to fulfill automation tasks.

# Request:
{user_input}

# Repo structure:
{repo_tree}

For each step, output either:
```bash
<shell command>
or
<file content>
"""

def run_agent_loop(repo_name, user_input):
    prompt = build_prompt(user_input, repo_name)
    history = prompt
    for _ in range(10):  # Limit number of LLM calls to avoid infinite loops
        llm_output = call_llm(history)
        yield f"\n🧠 LLM Output:\n{llm_output}\n"

        action_type, payload = parse_action(llm_output)

        if action_type == "command":
            for output in run_shell_command(payload):
                yield output
            history += f"\nResult:\nExecuted command:\n{payload}\n"

        elif action_type == "file":
            path, content = payload
            result = write_file(os.path.join(repo_name, path), content)
            yield result
            history += f"\nResult:\n{result}\n"

        elif action_type == "done":
            yield "\n🎉 Task complete!"
            break

        else:
            yield "\n⚠️ Couldn't understand LLM output. Stopping."
            break
