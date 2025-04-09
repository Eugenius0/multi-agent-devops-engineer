import ollama

class PromptEngineerAgent:
    def __init__(self, model_name):
        self.model_name = model_name
        self.llm = ollama
        
    def build_prompt(self, user_input):
        return [
            {
                "role": "system",
                "content": (
                    "You are a DevOps prompt engineer.\n\n"
                    "Your job is to take a vague or natural language user input and rewrite it as a precise, technical DevOps automation instruction.\n"
                    "Your output will be used directly by another agent to generate shell commands.\n\n"
                    "If the task requires multiple steps, clearly describe them in order, including tooling used (e.g., Docker, GitHub Actions, Kubernetes, AWS CLI)."
                    "Use imperative style and include what the final output or goal should be."
                    "Guidelines:\n"
                    "- Be specific and unambiguous.\n"
                    "- Remove filler words or conversational phrases.\n"
                    "- Convert goals into technical steps when possible.\n"
                    "- Do not include explanations, just output the refined task.\n"
                    "- Use imperative style (e.g., 'Create', 'Setup', 'Generate').\n\n"
                    "Examples:\n"
                    "- Input: 'Can you help me set up CI/CD for my repo?'\n"
                    "- Output: 'Set up a GitHub Actions workflow that runs tests and builds the app on push to main.'\n\n"
                    "- Input: 'I want to dockerize it'\n"
                    "- Output: 'Generate a Dockerfile and docker-compose.yaml for the current app.'"
                )
            },
            {
                "role": "user",
                "content": f"Original user input: {user_input}\nRefactor it into a clean and precise DevOps instruction."
            }
        ]

    async def refine(self, user_input):
        messages = self.build_prompt(user_input)
        response = self.llm.chat(model=self.model_name, messages=messages)
        return response["message"]["content"]