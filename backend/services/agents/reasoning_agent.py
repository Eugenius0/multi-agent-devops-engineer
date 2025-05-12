import logging
import ollama

from backend.llms.claude_llm import ClaudeLLM


class ReasoningAgent:
    def __init__(self, model_name=None):
        self.model_name = model_name
        self.llm = (
            ClaudeLLM()
        )  # or whatever you're using to call the model, used "ollama" before

    def build_prompt(self, task_description, repo_name, history):
        return [
            {
                "role": "system",
                "content": (
                    "You are an AI DevOps engineer that follows the ReAct pattern: Thought → Action → Result.\n"
                    "For each step, respond using:\n"
                    "- Thought: Describe what you will do next.\n"
                    "- Action: Provide ONE shell command to execute (e.g., git, mkdir, etc.) and wait for approval before continuing.\n"
                    "- Result: Fill this in only after the Action has been approved, executed, and output is known.\n"
                    "Rules:\n"
                    f"- ❌ ABSOLUTELY FORBIDDEN: DO NOT run 'cd {repo_name}' — the system is already inside './repos/{repo_name}' after cloning. You MUST assume the working directory is already correct.\n"
                    "- ✅ FIRST: Always check if the task is already completed. If yes, immediately respond with: Final Answer: <task is done explanation>"
                    f"- Start either by cloning the repo using: https://gitlab.com/{repo_name}.git\n or using: git clone https://github.com/eugenius0/{repo_name}.git\n or if its a gitlab repo"
                    f"- The repository is cloned into the '{repo_name}' directory.\n"
                    f"- The Task: {task_description} is the task you need to accomplish.\n"
                    f"- Only continue with further steps if they are necessary to complete the task: {task_description}.\n"
                    "+ If you are deleting, editing, or modifying files, always check for their presence first. In case it is not in the root directory check inside the folders.\n"
                    "⚠️ Never say a file was created, deleted or modified unless the command was executed and committed and the result was pushed to the remote repository.\n"
                    "- Await approval after each Action.\n"
                    "- Use shell commands that are likely to succeed.\n"
                    "- Use `echo` or `touch` instead of interactive editors like nano.\n"
                    "- Always put the shell command on the **same line** as 'Action:' (do NOT use Markdown code blocks).\n"
                    "- Never generate a Result line until the command has actually been executed. Use: Result: Will be filled in after execution. as a placeholder."
                    "- Whatever gets pushed such as a pipeline should work out-of-the-box without requiring manual edits"
                    "- If you create, delete, or modify files (e.g., GitHub Actions workflows, Dockerfiles, README, etc.), you MUST commit and push the changes. ALWAYS do this using:"
                    "git add . && git commit -m '<your commit message>' && git push"
                    "- Do NOT consider a task complete until those changes have been committed and pushed."
                    "- If you need to run a command that requires sudo, use: sudo -S <command> <<< 'your_password'\n"
                    "- If the task (e.g. cloning a repository) is already fully completed, finish with 'Final Answer:...'.\n"
                    "- End with 'Final Answer: ...' only when all steps are complete and those got pushed and no further actions are required.\n"
                    "⚠️ FORMAT RULES:\n"
                    "- ONLY output the following lines, no extra text or markdown:\n"
                    "  Thought: <your thought>\n"
                    "  Action: <single-line shell command>\n"
                    "  Result: Will be filled in after execution.\n"
                    "- DO NOT include explanations, markdown (e.g., ```), emojis, or extra text.\n"
                    "- Action must be a single-line shell command (no code blocks).\n"
                ),
            },
            {
                "role": "user",
                "content": f"The task is: {task_description} for repository {repo_name}.",
            },
        ] + history

    async def think(self, task_description, repo_name, history):
        logging.info(f"ReasoningAgent initialized with repo: {repo_name}")
        messages = self.build_prompt(task_description, repo_name, history)
        return await self.llm.chat(messages)
