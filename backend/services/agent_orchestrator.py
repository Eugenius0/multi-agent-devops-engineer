from .agents.reasoning_agent import ReasoningAgent
from .agents.prompt_agent import PromptEngineerAgent
from .agents.reflector_agent import ReflectorAgent
import asyncio
import uuid
import os
import subprocess
import re
from backend.services.state import approval_channels, cancelled_tasks

class AgentOrchestrator:
    def __init__(self, model_name="qwen2.5-coder:7b"):
        self.reasoning_agent = ReasoningAgent(model_name)
        self.prompt_engineer = PromptEngineerAgent(model_name)
        self.reflector_agent = ReflectorAgent(model_name)

    async def run(self, task_id, repo_name, user_input):
        approval_q = asyncio.Queue()
        history = []
        approval_channels[task_id] = approval_q

        refined_input = await self.prompt_engineer.refine(user_input)
        yield f"\n🧠 Refined Task: {refined_input}"

        repo_path = f"./repos/{repo_name}"
        if os.path.exists(repo_path):
            history.append({
                "role": "user",
                "content": f"The repository {repo_name} is already cloned locally into {repo_path}. You are already in the correct directory. DO NOT clone again or use 'cd'."
            })
                # Check if repo is behind origin/main
            try:
                result = subprocess.run(
                    ["git", "remote", "update"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )

                rev_list = subprocess.run(
                    ["git", "rev-list", "HEAD...origin/main", "--count"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )

                if rev_list.returncode == 0 and rev_list.stdout.strip() != "0":
                    history.append({
                        "role": "user",
                        "content": f"The local repository {repo_name} is out of sync with origin/main. Automatically pulling latest changes..."
                    })

                    try:
                        pull_result = subprocess.run(
                            ["git", "pull", "origin", "main"],
                            cwd=repo_path,
                            capture_output=True,
                            text=True
                        )
                        if pull_result.returncode == 0:
                            history.append({
                                "role": "user",
                                "content": f"✅ Successfully pulled latest changes:\n{pull_result.stdout.strip()}"
                            })
                        else:
                            history.append({
                                "role": "user",
                                "content": f"❌ Failed to pull latest changes:\n{pull_result.stderr.strip()}"
                            })
                    except Exception as e:
                        history.append({
                            "role": "user",
                            "content": f"❌ Exception while pulling latest changes: {str(e)}"
                        })

                else:
                    history.append({
                        "role": "user",
                        "content": f"The local repository {repo_name} is up to date with origin/main."
                    })

            except Exception as e:
                history.append({
                    "role": "user",
                    "content": f"⚠️ Failed to check sync status for {repo_name}. Reason: {str(e)}"
                })

            else:
                history.append({
                    "role": "user",
                    "content": f"The repository {repo_name} is NOT cloned yet. Start by cloning it using: git clone https://github.com/eugenius0/{repo_name}.git"
                })



        while True:
            # 🔍 Get LLM output
            thought_output = await self.reasoning_agent.think(refined_input, repo_name, history)

            # ✅ Extract action before appending to history
            action = extract_action(thought_output)

            # Ensure the Result line is a placeholder before execution
            if "Result:" in thought_output and "Will be filled in after execution" not in thought_output:
                yield "\n⚠️ Warning: The agent hallucinated a Result. Retrying with corrected instruction..."

                history.append({
                    "role": "user",
                    "content": (
                        "⚠️ You included a real Result before the Action was approved or executed. "
                        "Please only use: Result: Will be filled in after execution.\n"
                        "Try again with the same Thought and Action, but follow the structure strictly."
                    )
                })

            yield f"\n🧠 {thought_output}"
            history.append({"role": "assistant", "content": thought_output})


            # ✅ Check if task is complete
            if "Final Answer" in thought_output:
                yield "\n✅ Task complete."
                break

            # ❌ Handle missing action
            if not action:
                yield "\n⚠️ No action found. Aborting."
                break

            # 🔁 Approval step
            step_id = str(uuid.uuid4())
            approval_channels[step_id] = approval_q
            yield f"\n[ApprovalRequired] {step_id} → {action}"
            yield "\n⏸ Awaiting user approval..."

            approval = await approval_q.get()
            if not approval["approved"]:
                yield "\n❌ Action rejected by user. Asking Reflector Agent for an alternative..."

                # Ask reflector for a better version of the rejected command
                rejected_command = approval["edited_command"] or action
                recovery = await self.reflector_agent.suggest_fix(rejected_command, "User rejected this action.", repo_name)
                yield f"\n🔄 Reflector Agent Suggestion:\n{recovery}"

                history.append({"role": "user", "content": f"User rejected the action. Try this instead:\n{recovery}"})
                continue

            # 🧨 Execute the (possibly edited) action
            used_command = approval["edited_command"] or action
            result = execute_action(used_command, repo_name)
            yield f"\n📄 Result: {result}"
            history.append({"role": "user", "content": f"Result: {result}"})

            # 🛠 If failed, ask ReflectorAgent to suggest a fix
            if result.startswith("❌"):
                recovery = await self.reflector_agent.suggest_fix(action, result, repo_name)
                yield f"\n🔄 Reflector Agent Suggestion:\n{recovery}"
                history.append({"role": "user", "content": f"Error occurred. Try this instead:\n{recovery}"})


# --- Helper functions ---

def extract_action(content: str) -> str:
    """
    Extracts the shell command from a message containing 'Action:'.
    Supports both inline and Markdown code block formats.
    """
    lines = content.splitlines()
    inline_action = _extract_inline_action(lines)
    if inline_action:
        return inline_action

    return _extract_block_action(lines)


def _extract_inline_action(lines):
    """Extracts an inline action if present."""
    for line in lines:
        if line.strip().lower().startswith("action:"):
            inline = line.split(":", 1)[1].strip()
            if inline:
                return inline
    return None


def _extract_block_action(lines):
    """Extracts a block action from code blocks."""
    in_action_block = False
    inside_code_block = False
    command_lines = []

    for line in lines:
        if _is_action_start(line):
            in_action_block = True
            continue

        if in_action_block:
            if _toggle_code_block(line):
                inside_code_block = not inside_code_block
                continue

            _process_command_line(line, inside_code_block, command_lines)

    return "\n".join(command_lines).strip() if command_lines else ""


def _is_action_start(line):
    """Checks if the line starts an action block."""
    return line.strip().lower().startswith("action:")


def _toggle_code_block(line):
    """Toggles the state of being inside a code block."""
    return re.match(r"^```(?:bash)?", line.strip())


def _process_command_line(line, inside_code_block, command_lines):
    """Processes a line and adds it to command_lines if valid."""
    if inside_code_block or line.strip():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):  # skip comment lines
            command_lines.append(stripped)


def execute_action(command: str, repo_name: str) -> str:
    """Executes a shell command using the proper working directory."""
    base_dir = "./repos"
    os.makedirs(base_dir, exist_ok=True)

    is_clone = command.strip().startswith("git clone")
    cwd = base_dir if is_clone else os.path.join(base_dir, repo_name)

    if not is_clone and not os.path.exists(cwd):
        return f"❌ Error: Repository directory does not exist: {cwd}"

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, cwd=cwd
        )
        if result.returncode == 0:
            return result.stdout.strip() or f"✅ Successfully executed: {command}"
        else:
            return f"❌ Command failed with error:\n{result.stderr.strip()}"
    except subprocess.CalledProcessError as e:
        return f"❌ Command execution error:\n{str(e)}"


def cancel_execution():
    """Cancel all pending approval tasks."""
    cancelled_tasks.update(approval_channels.keys())
