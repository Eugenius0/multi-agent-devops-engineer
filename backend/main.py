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

@app.post("/run-automation")
async def run_automation(request: UserRequest):
    """Uses DeepSeek Coder v2 to determine which automation to run."""
    user_input = request.user_input

    if not user_input:
        raise HTTPException(status_code=400, detail="No user input provided")

    # Query the LLM to determine which automation to run
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": f"""
            You are an AI assistant. Your task is to extract the correct automation type from a user request. 
            Options are: 'GitHub Actions', 'Docker', 'GitHub Actions and Docker'. 
            Do NOT provide any explanation—ONLY return one of these exact options.
        
            User request: {user_input}
        """}]
    )


    # Clean the response to remove extra quotes
    try:
        intent = ast.literal_eval(response['message']['content'].strip())
    except (SyntaxError, ValueError):
        intent = response['message']['content'].strip()

    # Ensure intent is a string
    intent = intent if isinstance(intent, str) else str(intent)

    # Validate the intent returned by LLM
    if intent not in ["GitHub Actions", "Docker", "GitHub Actions and Docker"]:
        return {"error": "LLM returned an unrecognized intent.", "llm_output": intent}

    # Generate a unique task ID
    task_id = str(uuid.uuid4())
    task_status[task_id] = "Running"

    # Execute the appropriate automation script based on LLM decision
    if intent == "GitHub Actions":
        output = run_script("setup_github_actions.py")
    elif intent == "Docker":
        output = run_script("dockerize_app.py")
    elif intent == "GitHub Actions and Docker":
        output = run_script("setup_github_actions.py") + "\n" + run_script("dockerize_app.py")

    task_status[task_id] = "Completed"

    return {"task_id": task_id, "status": "Completed", "executed_task": intent, "output": output}

@app.get("/get-status/{task_id}")
async def get_status(task_id: str):
    """Returns the status of an automation task."""
    status = task_status.get(task_id, "Not Found")
    return {"task_id": task_id, "status": status}

@app.get("/get-logs/{task_id}")
async def get_logs(task_id: str):
    """Returns logs for the given task ID."""
    logs = f"Logs for task {task_id}"
    return {"task_id": task_id, "logs": logs}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
