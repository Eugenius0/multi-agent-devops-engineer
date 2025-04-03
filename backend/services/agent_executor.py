import asyncio
import logging
import os
import ollama
import uuid
import subprocess

# Shared dictionary to manage pending approvals
approval_channels = {}  # key: task_id, value: asyncio.Queue
cancelled_tasks = set()  # Track task IDs that should be cancelled

MODEL_NAME = "deepseek-coder-v2"

async def run_agent_loop(task_id: str, repo_name: str, user_input: str):
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
            "- Always start by cloning the GitHub/GitLab repository before anything else.\n"
            "- Use the default username and repo name provided below.\n"
            "- Use this command format exactly:\n"
            "  Action: git clone https://github.com/eugenius0/<repo>.git unless its a gitlab repo then do https://gitlab.com/<repo>.git\n\n" #eugenius0 is the hardcoded username
            "- Do NOT use `nano`. Instead, write files using shell redirection like echo or heredoc (cat <<EOF ...).\n"
            "- Do NOT use `cd` commands. The system already executes each command in the correct working directory.\n"
            "- Only provide raw shell commands in the Action line, no markdown or explanation.\n"
            "- If a workflow file or pipeline or whatever affected file already exists, update that file instead of creating a new one.\n"
            "After writing or modifying any file, make sure to run the following to save changes: 1. git add . 2. git commit -m your message 3. git push origin main."
            "Do this at the end of the task to finalize the automation."
            "- Wait for user approval after every Action before proceeding.\n"
            "- End the process with: Final Answer: ... when done."
        )
        },
        {"role": "user", "content": f"The task is: {user_input} for repository '{repo_name}'."}
    ]

    while True:
        # Call the model for next reasoning step
        response = ollama.chat(model=MODEL_NAME, messages=messages)
        content = response["message"]["content"]
        messages.append({"role": "assistant", "content": content})

        yield f"\n🧠 {content}"

        if task_id in cancelled_tasks:
            yield "\n❌ Execution cancelled by user."
            break

        # Stop if task is marked as complete
        if "Final Answer" in content:
            yield "\n✅ All steps completed."
            break

        # Extract and wait for user approval if there's an Action
        action = extract_action(content)
        if action:
            task_id = str(uuid.uuid4())
            approval_q = asyncio.Queue()
            approval_channels[task_id] = approval_q  # ✅ register the approval channel

            yield f"\n[ApprovalRequired] {task_id} → {action}"
            yield "\n⏸ Awaiting user approval..."

            # ⏳ Wait here until /approve-action puts into the queue
            approval_response = await approval_q.get()
            if task_id in cancelled_tasks:
                yield "\n❌ Execution cancelled before user approval."
                break

            approved = approval_response["approved"]
            edited_command = approval_response.get("edited_command") or action

            if approved:
                result = execute_action(edited_command, repo_name)
                messages.append({"role": "user", "content": f"Result: {result}"})
                yield f"\n📝 Executed: {edited_command}"
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
    


running_process = None  # Legacy compatibility (can stay None)
stop_execution = False  # Optional global flag for cancellation

def cancel_execution():
    """Legacy cancellation hook for compatibility."""
    cancelled_tasks.update(approval_channels.keys())

