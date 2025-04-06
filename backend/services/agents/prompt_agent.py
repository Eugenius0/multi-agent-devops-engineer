import ollama
from .base_agent import BaseAgent

class PromptEngineerAgent(BaseAgent):
    def __init__(self, model_name):
        self.model_name = model_name
        self.llm = ollama
        
    def build_prompt(self, user_input):
        return [
            {
                "role": "system",
                "content": (
                    "You are a prompt engineer. Your job is to optimize user tasks into a single precise DevOps automation task."
                )
            },
            {
                "role": "user",
                "content": f"Original user input: {user_input}\nRefactor it into a clean and precise instruction for a DevOps agent."
            }
        ]

    async def refine(self, user_input):
        messages = self.build_prompt(user_input)
        response = self.llm.chat(model=self.model_name, messages=messages)
        return response["message"]["content"]