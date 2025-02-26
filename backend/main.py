from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import ollama
import uuid
import ast
from services.executor import run_script
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow requests from any frontend (can get restricted later)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (POST, GET, etc.)
    allow_headers=["*"],  # Allow all headers
)

MODEL_NAME = "deepseek-coder-v2"  # Change to preferred model

# Store task statuses
task_status = {}

class UserRequest(BaseModel):
    user_input: str
    repo_name: str  # Added field for repository name

@app.post("/run-automation")
async def run_automation(request: UserRequest):
    """Uses DeepSeek Coder v2 to determine which automation to run."""
    user_input = request.user_input
    repo_name = request.repo_name.strip()

    if not user_input or not repo_name:
        raise HTTPException(status_code=400, detail="User input and repo name are required")

    response = ollama.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": f"""
            You are an AI assistant. Your task is to extract the correct automation type from a user request. 
            Options are: 'GitHub Actions', 'Docker', 'GitHub Actions and Docker'. 
            Do NOT provide any explanation—ONLY return one of these exact options.
        
            User request: {user_input}
        """}]
    )

    try:
        intent = ast.literal_eval(response['message']['content'].strip())
    except (SyntaxError, ValueError):
        intent = response['message']['content'].strip()

    if intent not in ["GitHub Actions", "Docker", "GitHub Actions and Docker"]:
        return {"error": "LLM returned an unrecognized intent.", "llm_output": intent}

    task_id = str(uuid.uuid4())
    task_status[task_id] = "Running"

    if intent == "GitHub Actions":
        output = run_script("setup_github_actions.py", repo_name)
    elif intent == "Docker":
        output = run_script("dockerize_app.py", repo_name)
    elif intent == "GitHub Actions and Docker":
        output = run_script("setup_github_actions.py", repo_name) + "\n" + run_script("dockerize_app.py", repo_name)

    task_status[task_id] = "Completed"

    return {"task_id": task_id, "status": "Completed", "executed_task": intent, "output": output}
