from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI()

CORRELATION_ENGINE_URL = "http://localhost:8001/alerts"


@app.get("/")
def home():
    return {"message": "Alert Ingestion Service is running"}


class Alert(BaseModel):
    alertname: str
    resource_id: str
    severity: str


def forward_to_correlation_engine(alert_data):
    # Send one alert to the Correlation Engine and return its reply
    try:
        response = requests.post(CORRELATION_ENGINE_URL, json=alert_data)
        return response.json()
    except requests.exceptions.ConnectionError:
        print("Could not reach the Correlation Engine")
        return {"error": "Correlation Engine is not reachable"}


# For manual testing with curl (our own simple format)
@app.post("/webhook/alert")
def receive_alert(alert: Alert):
    print(f"Received alert: {alert.alertname} for {alert.resource_id}")
    alert_data = {
        "alertname": alert.alertname,
        "resource_id": alert.resource_id,
        "severity": alert.severity,
    }
    result = forward_to_correlation_engine(alert_data)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "forwarded", "correlation_result": result}


# Called by Prometheus Alertmanager (its own, larger format)
@app.post("/webhook/alertmanager")
def receive_from_alertmanager(payload: dict):
    forwarded = []
    for item in payload.get("alerts", []):
        labels = item.get("labels", {})
        name = labels.get("alertname", "unknown")

        # Only firing alerts start work; "resolved" notices are ignored for now
        if item.get("status") != "firing":
            print(f"Ignoring {item.get('status')} notice for {name}")
            continue

        alert_data = {
            "alertname": name,
            "resource_id": labels.get("resource_id") or labels.get("instance", "unknown"),
            "severity": labels.get("severity", "warning"),
        }
        print(f"Alertmanager alert: {alert_data['alertname']} for {alert_data['resource_id']}")
        forwarded.append(forward_to_correlation_engine(alert_data))

    return {"status": "processed", "forwarded": forwarded}