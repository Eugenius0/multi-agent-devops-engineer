import ollama
from .base_agent import BaseAgent

class ReasoningAgent(BaseAgent):
    def __init__(self, model_name):
        self.model_name = model_name
        self.llm = ollama  # or whatever you're using to call the model
        
    def build_prompt(self, task_description, history):
        return [
            {
                "role": "system",
                "content": (
                    "You are an AI DevOps engineer that follows the ReAct pattern: Thought → Action → Result.\n"
                    "For each step, respond using:\n"
                    "- Thought: Describe what you will do next.\n"
                    "- Action: Provide ONE shell command to execute (e.g., git, mkdir, etc.).\n"
                    "- Result: Will be filled in after execution.\n\n"
                    "Rules:\n"
                    "- Start by cloning the GitHub/GitLab repo.\n"
                    "- Use `echo`, `cat <<EOF` instead of nano.\n"
                    "- Don't use `cd` commands.\n"
                    "- Update files if they exist.\n"
                    "- After modifying files: git add . && git commit && git push\n"
                    "- Await approval after each Action.\n"
                    "- End with 'Final Answer: ...' when complete."
                )
            },
            {"role": "user", "content": f"The task is: {task_description}"}
        ] + history

    async def think(self, task_description, history):
        messages = self.build_prompt(task_description, history)
        response = self.llm.chat(model=self.model_name, messages=messages)
        return response["message"]["content"]

