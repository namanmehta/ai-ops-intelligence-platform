from fastapi import FastAPI
from pydantic import BaseModel
from orchestrator_agent import run_orchestrator
from tools import REMEDIATION_PROPOSALS

app = FastAPI()

conversation = []

class InvestigateRequest(BaseModel):
    task: str

@app.post("/investigate")
def investigate(request: InvestigateRequest):
    conversation.append({"role": "user", "content": request.task})
    report = run_orchestrator(conversation)
    return {"report": report}

@app.post("/reset")
def reset():
    conversation.clear()
    return {"status": "reset"}

@app.get("/proposals")
def get_proposals():
    return REMEDIATION_PROPOSALS

@app.post("/proposals/{proposal_id}/approve")
def approve_proposal(proposal_id: str):
    for p in REMEDIATION_PROPOSALS:
        if p["proposal_id"] == proposal_id:
            p["status"] = "approved"
            print(f"\n[SIMULATED EXECUTION] Running action '{p['action']}' on {p['pipeline_id']}")
            p["status"] = "executed"
            return p
    return {"error": "proposal not found"}

@app.post("/proposals/{proposal_id}/reject")
def reject_proposal(proposal_id: str):
    for p in REMEDIATION_PROPOSALS:
        if p["proposal_id"] == proposal_id:
            p["status"] = "rejected"
            return p
    return {"error": "proposal not found"}