import logging
import ollama

class ReasoningAgent:
    def __init__(self, model_name):
        self.model_name = model_name
        self.llm = ollama  # or whatever you're using to call the model
        
    def build_prompt(self, task_description, repo_name, history):
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
                    "- ALWAYS start by checking if the GitHub repo is cloned locally at ./repos/{repo_name}. If not, clone it using: git clone https://github.com/eugenius0/{repo_name}.git\n"
                    "- NEVER skip this check or try to mkdir manually.\n"
                    "- Assume you are working inside the repo directory after cloning.\n"
                    "- Use `echo`, `cat <<EOF` instead of nano.\n"
                    "- Always put the shell command on the **same line** as 'Action:' (no Markdown code blocks)\n"
                    "- ALWAYS use this exact placeholder text after Action: `Result: Will be filled in after execution.`\n"
                    "- DO NOT guess or simulate the result.\n"
                    "- After modifying files: git add . && git commit -m 'message' && git push\n"
                    "- Await user approval after every Action.\n"
                    "- Use 'Final Answer: ...' only when the task is truly done."

            )
            },
            {"role": "user", "content": f"The task is: {task_description} for repository {repo_name}."},
        ] + history

    async def think(self, task_description, repo_name, history):
        logging.info(f"ReasoningAgent initialized with repo: {repo_name}")
        messages = self.build_prompt(task_description, repo_name, history)
        response = self.llm.chat(model=self.model_name, messages=messages)
        return response["message"]["content"]

