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
            inc["alerts"].append(alert.alertname)
            inc["last_seen"] = now
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