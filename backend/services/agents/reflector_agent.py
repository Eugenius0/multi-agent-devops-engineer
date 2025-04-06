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
                "content": "You are an AI DevOps troubleshooting agent. Your task is to reflect on failed shell commands and suggest alternatives."
            },
            {
                "role": "user",
                "content": f"The command `{action}` failed with error:\n{error_output}\n\nSuggest a new shell command or a workaround."
            }
        ]

    async def suggest_fix(self, action, error_output):
        messages = self.build_prompt(action, error_output)
        response = self.llm.chat(model=self.model_name, messages=messages)
        return response["message"]["content"]