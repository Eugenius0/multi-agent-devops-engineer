import asyncio
import logging
import os
import ollama
import uuid
import time
import subprocess

# Shared dictionary to manage pending approvals
approval_queue = {}

async def run_agent_loop(repo_name: str, user_input: str):
    """
    Loop: LLM thinks, generates Action (command or code), waits for approval, then executes.
    """
    messages = [
        {
            "role": "system",
            "content": (
            "You are an AI DevOps engineer that follows the ReAct pattern: Thought → Action → Result.\n"
            "For each step, respond using:\n"
            "- Thought: Describe what you will do next.\n"
            "- Action: Provide ONE shell command to execute (e.g., git, mkdir, nano, etc.).\n"
            "- Result: Will be filled in after execution.\n\n"
            "Important rules:\n"
            "- Always start by cloning the GitHub repository before anything else.\n"
            "- Use the default username and repo name provided below.\n"
            "- Use this command format exactly:\n"
            "  Action: git clone https://github.com/eugenius0/<repo>.git\n\n" #eugenius0 is the hardcoded username
            "- Use `nano` to create or edit files (do not use echo).\n"
            "- Only provide raw shell commands in the Action line, no markdown or explanation.\n"
            "- Wait for user approval after every Action before proceeding.\n"
            "- End the process with: Final Answer: ... when done."
        )
        },
        {"role": "user", "content": f"The task is: {user_input} for repository '{repo_name}'."}
    ]

    while True:
        # Call the model for next reasoning step
        response = ollama.chat(model="deepseek-coder-v2", messages=messages)
        content = response["message"]["content"]
        messages.append({"role": "assistant", "content": content})

        yield f"\n🧠 {content}"

        # Stop if task is marked as complete
        if "Final Answer" in content:
            yield "\n✅ All steps completed."
            break

        # Extract and wait for user approval if there's an Action
        action = extract_action(content)
        if action:
            task_id = str(uuid.uuid4())
            approval_queue[task_id] = {"action": action, "approved": None}
            yield "\n⏸ Awaiting user approval..."
            yield f"\n[ApprovalRequired] {task_id} → {action}"

            while approval_queue[task_id]["approved"] is None:
                await asyncio.sleep(1)  # ✅ non-blocking wait

            if approval_queue[task_id]["approved"]:
                result = execute_action(action, repo_name)
                messages.append({"role": "user", "content": f"Result: {result}"})
                yield f"\n✅ Executed: {action}"
                yield f"\n📄 Result: {result}"
            else:
                yield "\n❌ Action was rejected by the user. Stopping execution."
                break


def run_command(command, capture_output=True, cwd=None):
    """Executes a shell command with optional output capture and working directory."""
    try:
        if capture_output:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=cwd)
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        else:
            subprocess.run(command, shell=True, check=True, cwd=cwd)
            logging.info(f"✅ Successfully executed: {command}")
            return 0, None, None  # Success with no captured output
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Error executing: {command}\n{e}")
        return e.returncode, None, str(e)  # Return error details


def extract_action(content: str) -> str:
    """
    Extracts the first Action: line from the LLM output.
    """
    for line in content.splitlines():
        if line.strip().lower().startswith("action:"):
            return line.split(":", 1)[1].strip()
    return ""


def execute_action(command: str, repo_name: str) -> str:
    """
    Executes the given shell command using the proper working directory.
    """
    base_dir = "./repos"
    os.makedirs(base_dir, exist_ok=True)

    is_clone = command.strip().startswith("git clone")
    cwd = base_dir if is_clone else os.path.join(base_dir, repo_name)

    if not is_clone and not os.path.exists(cwd):
        return f"❌ Error: Repository directory does not exist: {cwd}"

    code, out, err = run_command(command, cwd=cwd)

    if code == 0:
        return out or f"✅ Successfully executed: {command}"
    else:
        return f"❌ Command failed with error:\n{err}"
