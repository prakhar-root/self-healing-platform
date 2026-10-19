from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime, timedelta
import uuid

app = FastAPI()


@app.get("/")
def home():
    return {"message": "Correlation Engine is running"}


incidents = {}


class Alert(BaseModel):
    alertname: str
    resource_id: str
    severity: str


CORRELATION_WINDOW = timedelta(minutes=5)


def severity_rank(severity):
    return {"warning": 1, "critical": 2}.get(severity, 0)


@app.post("/alerts")
def receive_alert(alert: Alert):
    now = datetime.utcnow()

    # Step 1: check every existing incident for a match
    for inc in incidents.values():
        if (
            inc["resource_id"] == alert.resource_id
            and inc["status"] == "open"
            and now - inc["last_seen"] <= CORRELATION_WINDOW
        ):
            if alert.alertname not in inc["alerts"]:
                inc["alerts"].append(alert.alertname)
            inc["last_seen"] = now
            if severity_rank(alert.severity) > severity_rank(inc["severity"]):
                inc["severity"] = alert.severity
            return {"incident_id": inc["incident_id"], "action": "merged"}

    # Step 2: no match found -> create a new incident
    incident_id = f"inc-{uuid.uuid4().hex[:8]}"
    incidents[incident_id] = {
        "incident_id": incident_id,
        "resource_id": alert.resource_id,
        "alerts": [alert.alertname],
        "severity": alert.severity,
        "status": "open",
        "first_seen": now,
        "last_seen": now,
    }
    return {"incident_id": incident_id, "action": "created"}


@app.get("/incidents")
def list_incidents(status: str = "open"):
    return [inc for inc in incidents.values() if inc["status"] == status]


@app.post("/incidents/{incident_id}/resolve")
def resolve_incident(incident_id: str, status: str):
    if incident_id not in incidents:
        return {"error": "incident not found"}
    if status not in ("auto_resolved", "escalated"):
        return {"error": "status must be auto_resolved or escalated"}
    incidents[incident_id]["status"] = status
    return incidents[incident_id]