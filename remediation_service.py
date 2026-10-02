from fastapi import FastAPI
import requests

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Remediation Service is running"}



@app.get("/check")
def check_incidents():
    response = requests.get("http://localhost:8001/incidents")
    incidents = response.json()
    print(f"Found {len(incidents)} open incident(s)")
    return incidents