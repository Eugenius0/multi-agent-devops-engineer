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
                    "- Action: Provide ONE shell command to execute (e.g., git, mkdir, etc.) and wait for approval before continuing.\n"
                    "- Result: Fill this in only after the Action has been approved, executed, and output is known.\n"
                    "Rules:\n"
                    f"- Start by cloning the repo using: git clone https://github.com/eugenius0/{repo_name}.git\n"
                    "- If the repo is already cloned, assume the working directory is correct. NEVER use here cd command\n"
                    f"You are already inside ./repos/{repo_name}. All commands must assume this as the current directory. Do NOT include ./repos/... or use cd.\n"
                    "- Assume you are working inside the repo directory after cloning.\n"
                    f"+ You are already inside the ./repos/{repo_name} directory after cloning."
                    f"+ If unsure whether the file exists or what the repo contains, but this info is needed to fullfill the task: '{task_description}' then  use `ls`, `ls -a`, or `git status` to check"
                    f"- Only continue with further steps if they are necessary to complete the task: {task_description}.\n"
                    "+ If you are deleting, editing, or modifying files, always check for their presence first."
                    "⚠️ Never include 'Final Answer' unless all shell steps have been executed.\n"
                    "⚠️ Never say a file was created unless the command was executed and committed.\n"
                    "- Await approval after each Action.\n"
                    "- Use shell commands that are likely to succeed.\n"
                    "- Use `echo`, `cat <<EOF` or `touch` instead of interactive editors like nano.\n"
                    "- Always put the shell command on the **same line** as 'Action:' (do NOT use Markdown code blocks).\n"
                    "- Never generate a Result line until the command has actually been executed. Use: Result: Will be filled in after execution. as a placeholder."
                    "- Whatever gets pushed such as a pipeline should work out-of-the-box without requiring manual edits"
                    "- If you create or modify files (e.g., GitHub Actions workflows, Dockerfiles, README, etc.), you MUST commit and push the changes. Use:\n"
                    "  git add . && git commit -m '<your commit message>' && git push\n ALWAYS use those when something is created or modified.\n"
                    "- If you need to run a command that requires sudo, use: sudo -S <command> <<< 'your_password'\n"
                    "- If the task (e.g. cloning a repository) is already fully completed, finish with 'Final Answer:...'.\n"
                    "- End with 'Final Answer: ...' only when all steps are complete and no further actions are required.\n"
)
            },
            {"role": "user", "content": f"The task is: {task_description} for repository {repo_name}."},
        ] + history

    async def think(self, task_description, repo_name, history):
        logging.info(f"ReasoningAgent initialized with repo: {repo_name}")
        messages = self.build_prompt(task_description, repo_name, history)
        response = self.llm.chat(model=self.model_name, messages=messages)
        return response["message"]["content"]

