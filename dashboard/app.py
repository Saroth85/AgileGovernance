"""
Backlog-health dashboard + human-in-the-loop review — FastAPI backend.

Run:
    pip install -r requirements.txt
    python dashboard/seed_backlog.py          # build the demo backlog
    uvicorn dashboard.app:app --reload        # then open http://127.0.0.1:8000

Endpoints:
    GET  /                      -> dashboard UI
    GET  /api/metrics           -> backlog-health metrics
    GET  /api/queue             -> human review queue (borderline stories)
    POST /api/review/{id}       -> record a human decision {decision, reviewer}
    POST /api/assess            -> assess a new story {title, description}
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import governance_store as store

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="Agile Delivery Governance — Backlog Health")


class Decision(BaseModel):
    decision: str          # "approved" | "rejected"
    reviewer: str = "reviewer"


class NewStory(BaseModel):
    title: str
    description: str


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/metrics")
def metrics():
    return store.get_metrics()


@app.get("/api/queue")
def queue():
    return store.get_queue()


@app.post("/api/review/{story_id}")
def review(story_id: str, body: Decision):
    if body.decision not in ("approved", "rejected"):
        raise HTTPException(400, "decision must be 'approved' or 'rejected'")
    result = store.record_decision(story_id, body.decision, body.reviewer)
    if not result:
        raise HTTPException(404, f"story {story_id} not found")
    return {"ok": True, "story_id": story_id, "decision": body.decision}


@app.post("/api/assess")
def assess(body: NewStory):
    item = store.assess_story(body.title, body.description)
    return {"ok": True, "story_id": item["story_id"], "verdict": item["verdict"]}
