import ollama
from .base_agent import BaseAgent

class ReflectorAgent(BaseAgent):
    def __init__(self, model_name):
        self.model_name = model_name
        self.llm = ollama
        
    def build_prompt(self, action, error_output):
        return [
            {
                "role": "system",
                "content": (
                    "You are a DevOps troubleshooting AI assistant.\n\n"
                    "When a shell command fails, your job is to reflect on the error and suggest a better alternative command or a small workaround that solves the issue.\n\n"
                    "Guidelines:\n"
                    "- Be concise and actionable.\n"
                    "- DO NOT repeat the same failed command.\n"
                    "- Suggest commands that are likely to succeed (e.g., mkdir before cd, check spelling, verify repo URL).\n"
                    "- Only output one valid shell command OR a short set of sequential commands.\n"
                    "- Do NOT provide explanations.\n"
                    "- Output format: Action: <your new shell command(s)>"
                )
            },
            {
                "role": "user",
                "content": (
                    f"The following command failed:\n\n"
                    f"Command: {action}\n"
                    f"Error:\n{error_output}\n\n"
                    "Suggest an improved shell command or workaround."
                )
            }
        ]

    async def suggest_fix(self, action, error_output):
        messages = self.build_prompt(action, error_output)
        response = self.llm.chat(model=self.model_name, messages=messages)
        return response["message"]["content"]