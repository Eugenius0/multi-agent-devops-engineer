from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid
from backend.services.agent_orchestrator import AgentOrchestrator
from backend.services.agent_orchestrator import cancel_execution
from backend.services.state import approval_channels
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

app = FastAPI()

# Enable CORS to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow requests from any frontend (can be restricted later)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (POST, GET, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Store task statuses and LLM output history
task_status = {}
llm_outputs = {}

# Instantiate orchestrator
orchestrator = AgentOrchestrator()


class UserRequest(BaseModel):
    user_input: str
    repo_name: str


class ApprovalRequest(BaseModel):
    task_id: str
    approved: bool
    edited_command: str | None = None  # Allow user-edited command


@app.post("/run-automation")
async def run_automation(request: UserRequest):
    user_input = request.user_input.strip()
    repo_name = request.repo_name.strip()

    if not user_input or not repo_name:
        raise HTTPException(
            status_code=400, detail="User input and repo name are required"
        )

    task_id = str(uuid.uuid4())
    task_status[task_id] = "Running"

    async def log_stream():
        try:
            async for log in orchestrator.run(task_id, repo_name, user_input):
                yield log
            task_status[task_id] = "Completed"
            yield "\n✅ Task Completed!"
        except Exception as e:
            task_status[task_id] = "Failed"
            yield f"\n❌ Error: {str(e)}"

    return StreamingResponse(log_stream(), media_type="text/event-stream")


@app.post("/approve-action")
async def approve_action(request: ApprovalRequest):
    task_id = request.task_id
    if task_id not in approval_channels:
        raise HTTPException(
            status_code=404, detail="Task ID not found or already processed."
        )

    # 🧠 Put approval response directly into the channel
    await approval_channels[task_id].put(
        {
            "approved": request.approved,
            "edited_command": request.edited_command,
        }
    )

    return {
        "status": "acknowledged",
        "task_id": task_id,
        "approved": request.approved,
        "used_command": request.edited_command,
    }


@app.get("/get-llm-output/{task_id}")
async def get_llm_output(task_id: str):
    """Optional: Retrieve raw LLM output if you choose to store it."""
    if task_id not in llm_outputs:
        raise HTTPException(
            status_code=404, detail="Task ID not found or no LLM output available."
        )
    return {"llm_output": llm_outputs[task_id]}


@app.post("/cancel-automation")
async def cancel_automation():
    cancel_execution()
    return {"message": "Automation cancelled"}
