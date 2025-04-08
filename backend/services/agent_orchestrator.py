from .agents.reasoning_agent import ReasoningAgent
from .agents.prompt_agent import PromptEngineerAgent
from .agents.reflector_agent import ReflectorAgent
import asyncio
import uuid
import os
import subprocess
import re
from backend.services.state import approval_channels

class AgentOrchestrator:
    def __init__(self, model_name="deepseek-coder-v2"):
        self.reasoning_agent = ReasoningAgent(model_name)
        self.prompt_engineer = PromptEngineerAgent(model_name)
        self.reflector_agent = ReflectorAgent(model_name)

    async def run(self, task_id, repo_name, user_input):
        approval_q = asyncio.Queue()
        history = []
        approval_channels[task_id] = approval_q

        refined_input = await self.prompt_engineer.refine(user_input)
        yield f"\n🧠 Refined Task: {refined_input}"

        while True:
            full_response = await self.reasoning_agent.think(refined_input, repo_name, history)
            history.append({"role": "assistant", "content": full_response})
            yield f"\n🧠 {full_response}"

            if "Final Answer" in full_response:
                yield "\n✅ Task complete."
                break

            await self._process_response_blocks(full_response, repo_name, history, approval_q)

    async def _process_response_blocks(self, full_response, repo_name, history, approval_q):
        blocks = re.split(r"\n(?=Thought:)", full_response)
        for block in blocks:
            action = extract_action(block)
            if not action:
                continue

            step_id = str(uuid.uuid4())
            approval_channels[step_id] = approval_q
            yield f"\n[ApprovalRequired] {step_id} → {action}"
            yield "\n⏸ Awaiting user approval..."

            approval = await approval_q.get()
            if not approval["approved"]:
                await self._handle_rejection(action, approval, history)
                break

            await self._execute_and_handle_action(action, approval, repo_name, history)

    async def _handle_rejection(self, action, approval, history):
        yield "\n❌ Action rejected by user. Asking Reflector Agent for an alternative..."
        rejected_command = approval["edited_command"] or action
        recovery = await self.reflector_agent.suggest_fix(rejected_command, "User rejected this action.")
        yield f"\n🔄 Reflector Agent Suggestion:\n{recovery}"
        history.append({
            "role": "user",
            "content": f"User rejected the action. Try this instead:\n{recovery}"
        })

    async def _execute_and_handle_action(self, action, approval, repo_name, history):
        used_command = approval["edited_command"] or action
        result = execute_action(used_command, repo_name)
        yield f"\n📄 Result: {result}"
        history.append({"role": "user", "content": f"Result: {result}"})

        if result.startswith("❌"):
            recovery = await self.reflector_agent.suggest_fix(used_command, result)
            yield f"\n🔄 Reflector Agent Suggestion:\n{recovery}"
            history.append({
                "role": "user",
                "content": f"Error occurred. Try this instead:\n{recovery}"
            })




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
