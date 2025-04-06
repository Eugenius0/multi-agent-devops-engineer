from .agents.reasoning_agent import ReasoningAgent
from .agents.prompt_agent import PromptEngineerAgent
from .agents.reflector_agent import ReflectorAgent
import asyncio
import uuid
import os
import subprocess
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

        # Step 1: Refine the user input
        refined_input = await self.prompt_engineer.refine(user_input)
        yield f"\n🧠 Refined Task: {refined_input}"

        while True:
            thought_output = await self.reasoning_agent.think(refined_input, history)
            history.append({"role": "assistant", "content": thought_output})
            yield f"\n🧠 {thought_output}"

            if "Final Answer" in thought_output:
                yield "\n✅ Task complete."
                break

            action = extract_action(thought_output)
            if not action:
                yield "\n⚠️ No action found. Aborting."
                break

            step_id = str(uuid.uuid4())
            approval_channels[step_id] = approval_q
            yield f"\n[ApprovalRequired] {step_id} → {action}"
            yield "\n⏸ Awaiting user approval..."

            approval = await approval_q.get()
            if not approval["approved"]:
                history.append({
                    "role": "user",
                    "content": "The action was rejected. Try a different approach."
                })
                continue

            result = execute_action(approval["edited_command"] or action, repo_name)
            history.append({"role": "user", "content": f"Result: {result}"})
            yield f"\n📄 Result: {result}"

            if result.startswith("❌"):
                recovery = await self.reflector_agent.suggest_fix(action, result)
                history.append({"role": "user", "content": f"Error occurred. Try this instead:\n{recovery}"})
                yield f"\n🔄 Reflector Agent Suggestion:\n{recovery}"

# --- Helper functions ---

def extract_action(content: str) -> str:
    """Extracts the first Action: line from the LLM output."""
    for line in content.splitlines():
        if line.strip().lower().startswith("action:"):
            return line.split(":", 1)[1].strip()
    return ""

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

