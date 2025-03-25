from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import ollama
import uuid
import ast
from services.executor import cancel_execution
from services.agent_executor import run_agent_loop
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
    """Handles the full AI automation agent pipeline with streaming."""
    user_input = request.user_input.strip()
    repo_name = request.repo_name.strip()

    if not user_input or not repo_name:
        raise HTTPException(status_code=400, detail="User input and repo name are required")

    task_id = str(uuid.uuid4())
    task_status[task_id] = "Running"

    async def log_stream():
        """Streams the LLM-driven automation step-by-step."""
        try:
            process = run_agent_loop(repo_name, user_input)
            for log in process:
                yield log
            task_status[task_id] = "Completed"
            yield "\n✅ Task Completed!"
        except Exception as e:
            task_status[task_id] = "Failed"
            yield f"\n❌ Error: {str(e)}"

    return StreamingResponse(log_stream(), media_type="text/event-stream")

@app.get("/get-llm-output/{task_id}")
async def get_llm_output(task_id: str):
    """(Optional) Expose LLM output history if you store it later."""
    if task_id not in llm_outputs:
        raise HTTPException(status_code=404, detail="Task ID not found or no LLM output available.")
    return {"llm_output": llm_outputs[task_id]}

@app.post("/cancel-automation")
async def cancel_automation():
    """Immediately stops any running automation task."""
    cancel_execution()  # Call function to stop execution
    return {"message": "Automation cancelled"}
