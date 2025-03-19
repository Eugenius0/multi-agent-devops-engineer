from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import ollama
import uuid
import ast
from services.executor import cancel_execution, run_script
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

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

# Store task statuses and LLM output
task_status = {}
llm_outputs = {}  # Dictionary to store LLM outputs

class UserRequest(BaseModel):
    user_input: str
    repo_name: str  # Added field for repository name

@app.post("/run-automation")
async def run_automation(request: UserRequest):
    """Uses DeepSeek Coder v2 to determine which automation to run and streams logs."""
    user_input = request.user_input
    repo_name = request.repo_name.strip()

    if not user_input or not repo_name:
        raise HTTPException(status_code=400, detail="User input and repo name are required")

    response = ollama.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": f"""
            You are an AI assistant responsible for classifying automation tasks.
        
        **Task:** Based on the user request, return **only one** of these exact options:
        - `GitHub Actions`
        - `Docker`
        - `GitLab CI/CD`
        - `Kubernetes`
        
        **Rules:**
        - If the user mentions **GitHub Actions**, return **GitHub Actions**.
        - If the user mentions **Docker**, return **Docker**.
        - If the user mentions **GitLab pipeline** or **GitLab CI/CD**, return **GitLab CI/CD**.
        - If the request involves **Kubernetes**, **k8s**, **kubectl**, or **Minikube**, return **Kubernetes**
        - Do NOT return explanations or any extra text—**ONLY return the exact option.**
        
        **User Request:**
        {user_input}
        """}]
    )

    try:
        intent = ast.literal_eval(response['message']['content'].strip())
    except (SyntaxError, ValueError):
        intent = response['message']['content'].strip()

    if intent not in ["GitHub Actions", "Docker", "GitLab CI/CD", "Kubernetes"]:
        return {"error": "LLM returned an unrecognized intent.", "llm_output": intent}

    # Store the LLM response in a dictionary
    task_id = str(uuid.uuid4())
    task_status[task_id] = "Running"
    llm_outputs[task_id] = response['message']['content'].strip()

    async def log_stream():
        """Streams logs dynamically to the UI with real-time output."""
        if intent == "GitHub Actions":
            script_name = "setup_github_actions.py"
        elif intent == "Docker":
            script_name = "dockerize_app.py"
        elif intent == "GitLab CI/CD":
            script_name = "setup_gitlab_ci.py"
        elif intent == "Kubernetes":
            script_name = "setup_kubernetes.py"
        else:
            script_name = "setup_github_actions.py"

        process = run_script(script_name, repo_name, user_input)

        for log in process:
            yield log  # 🔄 Immediately send logs to the UI

        task_status[task_id] = "Completed"

        yield "✅ Task Completed!"

    return StreamingResponse(log_stream(), media_type="text/event-stream")

@app.get("/get-llm-output/{task_id}")
async def get_llm_output(task_id: str):
    """Fetches the stored LLM output for the given task ID."""
    if task_id not in llm_outputs:
        raise HTTPException(status_code=404, detail="Task ID not found or no LLM output available.")
    
    return {"llm_output": llm_outputs[task_id]}

@app.post("/cancel-automation")
async def cancel_automation():
    """Immediately stops any running automation task."""
    cancel_execution()  # Call function to stop execution
    return {"message": "Automation cancelled"}
