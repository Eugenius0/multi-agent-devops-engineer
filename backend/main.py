# main.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid
from services.executor import cancel_execution
from services.agent_executor import run_agent_loop, approval_queue
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

app = FastAPI()

# Enable CORS to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow requests from any frontend (can be restricted later)
    allow_credentials=True,
    allow_methods=["*"], # Allow all HTTP methods (POST, GET, etc.)
    allow_headers=["*"], # Allow all headers
)

MODEL_NAME = "deepseek-coder-v2"  # Model for reasoning

# Store task statuses and LLM output history
task_status = {}
llm_outputs = {}

class UserRequest(BaseModel):
    user_input: str
    repo_name: str

class ApprovalRequest(BaseModel):
    task_id: str
    approved: bool

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
        try:
            async for log in run_agent_loop(repo_name, user_input):
                yield log
            task_status[task_id] = "Completed"
            yield "\n✅ Task Completed!"
        except Exception as e:
            task_status[task_id] = "Failed"
            yield f"\n❌ Error: {str(e)}"


    return StreamingResponse(log_stream(), media_type="text/event-stream")

@app.post("/approve-action")
async def approve_action(request: ApprovalRequest):
    """Handles approval or rejection of an action from the frontend."""
    print("✅ Received approval for:", request.task_id, request.approved)
    task_id = request.task_id
    if task_id not in approval_queue:
        raise HTTPException(status_code=404, detail="Task ID not found or already processed.")
    
    approval_queue[task_id]["approved"] = request.approved
    return {"status": "acknowledged", "task_id": task_id, "approved": request.approved}

@app.get("/get-llm-output/{task_id}")
async def get_llm_output(task_id: str):
    """Optional: Retrieve raw LLM output if you choose to store it."""
    if task_id not in llm_outputs:
        raise HTTPException(status_code=404, detail="Task ID not found or no LLM output available.")
    return {"llm_output": llm_outputs[task_id]}

@app.post("/cancel-automation")
async def cancel_automation():
    """Cancels any active automation loop."""
    cancel_execution()
    return {"message": "Automation cancelled"}
