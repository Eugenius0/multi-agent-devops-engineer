from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import ollama
import subprocess
import uuid

app = FastAPI()

# Store task statuses
task_status = {}

class UserRequest(BaseModel):
    user_input: str

class AutomationRequest(BaseModel):
    intent: str

@app.post("/interpret-request")
async def interpret_request(request: UserRequest):
    user_input = request.user_input

    if not user_input:
        raise HTTPException(status_code=400, detail="No user input provided")

    response = ollama.chat(
        model="deepseek-coder-v2",
        messages=[{"role": "user", "content": f"Interpret this automation request: {user_input}"}]
    )

    interpreted_intent = response['message']['content']

    return {"intent": interpreted_intent}

@app.post("/run-automation")
async def run_automation(request: AutomationRequest):
    intent = request.intent

    if not intent:
        raise HTTPException(status_code=400, detail="No intent provided")

    task_id = str(uuid.uuid4())
    task_status[task_id] = "Running"

    if "GitHub Actions" in intent:
        script = "setup_github_actions.py"
    elif "Docker" in intent:
        script = "dockerize_app.py"
    elif "GitHub Actions" in intent and "Docker" in intent:
        script = "setup_github_and_docker.py"
    else:
        raise HTTPException(status_code=400, detail="Unknown intent")

    process = subprocess.Popen(["python", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    task_status[task_id] = "Completed"

    return {"task_id": task_id, "status": "Started", "script": script}

@app.get("/get-status/{task_id}")
async def get_status(task_id: str):
    status = task_status.get(task_id, "Not Found")
    return {"task_id": task_id, "status": status}

@app.get("/get-logs/{task_id}")
async def get_logs(task_id: str):
    logs = f"Logs for task {task_id}"
    return {"task_id": task_id, "logs": logs}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
