from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Alert Ingestion Service is running"}

class Alert(BaseModel):
    alertname: str
    resource_id: str
    severity: str

@app.post("/webhook/alert")
def receive_alert(alert: Alert):
    print(f"Received alert: {alert.alertname} for {alert.resource_id}")
    return {"status": "received", "alertname": alert.alertname}