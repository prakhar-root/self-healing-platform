from fastapi import FastAPI
import requests
import subprocess

app = FastAPI()


@app.get("/")
def home():
    return {"message": "Remediation Service is running"}


REMEDIATION_MAP = {
    "HighCPU": "scale_service.yml",
    "ContainerCrash": "restart_container.yml",
    "HealthCheckFailed": "restart_container.yml",
}


@app.get("/check")
def check_incidents():
    response = requests.get("http://localhost:8001/incidents")
    incidents = response.json()
    print(f"Found {len(incidents)} open incident(s)")
    return incidents


@app.get("/remediate")
def remediate():
    response = requests.get("http://localhost:8001/incidents")
    incidents = response.json()

    results = []
    for inc in incidents:
        playbook = None
        for alertname in inc["alerts"]:
            if alertname in REMEDIATION_MAP:
                playbook = REMEDIATION_MAP[alertname]
                break

        if playbook:
            print(f"Running {playbook} for {inc['resource_id']}")
            subprocess.run([
                "ansible-playbook", playbook,
                "-e", f"resource_id={inc['resource_id']}"
            ])
            results.append({
                "incident_id": inc["incident_id"],
                "action": "remediated",
                "playbook": playbook,
            })
        else:
            print(f"No known fix for {inc['resource_id']} - escalating")
            results.append({
                "incident_id": inc["incident_id"],
                "action": "escalated",
            })

    return results