import ollama

class ReflectorAgent:
    def __init__(self, model_name):
        self.model_name = model_name
        self.llm = ollama
        
    def build_prompt(self, action, repo_name, error_output):
        return [
            {
                "role": "system",
                "content": (
                    "You are a DevOps troubleshooting AI assistant.\n\n"
                    "Your job is to reflect on failed shell commands and suggest a valid, improved alternative.\n\n"
                    "Context:\n"
                    "- The user is running DevOps automation tasks inside a cloned GitHub repository.\n"
                    f"- All repositories are cloned into the './repos/{repo_name}' directory.\n"
                    f"- The current working directory is already './repos/{repo_name}'. NEVER use 'cd', 'repos/', or try to enter '{repo_name}' — you are already inside that directory.\n"
                    "- If the failed command includes `cd {repo_name}` or similar, strip the `cd` and just use the rest of the command (if any) as-is.\n"
                    "- If a file or folder is missing, check it with `ls`, `ls -a`, or `git status`.\n"
                    "- If deleting or modifying a file, always confirm it exists first using `ls` or `test -f`.\n"
                    "- If a command fails because something already exists (e.g., clone), assume it's available and continue.\n"
                    "- Prefer cautious exploratory commands before destructive actions.\n\n"
                    "Guidelines:\n"
                    "- Be concise and actionable.\n"
                    "- DO NOT repeat the same failed command.\n"
                    "- Only output one valid shell command OR a short sequential fallback (e.g. check then delete).\n"
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
                    f"Repository: {repo_name}\n\n"
                    "Your task is to suggest a better shell command that resolves the issue.\n"
                    "If the issue is context-related or unclear, you may propose a quick check using 'ls', 'git status', or 'test -f' to investigate."
                )
            }
        ]

    async def suggest_fix(self, action, repo_name, error_output):
        messages = self.build_prompt(action, repo_name, error_output)
        response = self.llm.chat(model=self.model_name, messages=messages)
        return response["message"]["content"]