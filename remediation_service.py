from contextlib import asynccontextmanager
from datetime import datetime
import subprocess
import threading
import time

from fastapi import FastAPI
import requests

CORRELATION_ENGINE = "http://localhost:8001"

# How often the service checks for open incidents (seconds)
CHECK_INTERVAL = 10
# An incident must be quiet for this long before we act on it, so related
# alerts that arrive a few seconds later can still join the same incident
SETTLE_SECONDS = 15

REMEDIATION_MAP = {
    "HighCPU": "scale_service.yml",
    "ContainerCrash": "restart_container.yml",
    "HealthCheckFailed": "restart_container.yml",
}

# Makes sure only one remediation run happens at a time
run_lock = threading.Lock()


def mark_incident(incident_id, status):
    # Tell the Correlation Engine how this incident ended
    requests.post(
        f"{CORRELATION_ENGINE}/incidents/{incident_id}/resolve",
        params={"status": status},
    )


def remediate_open_incidents(min_age_seconds=0):
    with run_lock:
        incidents = requests.get(f"{CORRELATION_ENGINE}/incidents").json()
        results = []

        for inc in incidents:
            # Skip incidents that are still receiving new alerts
            age = (datetime.utcnow() - datetime.fromisoformat(inc["last_seen"])).total_seconds()
            if age < min_age_seconds:
                continue

            playbook = None
            for alertname in inc["alerts"]:
                if alertname in REMEDIATION_MAP:
                    playbook = REMEDIATION_MAP[alertname]
                    break

            if playbook is None:
                print(f"No known fix for {inc['resource_id']} - escalating")
                mark_incident(inc["incident_id"], "escalated")
                results.append({"incident_id": inc["incident_id"], "action": "escalated"})
                continue

            print(f"Running {playbook} for {inc['resource_id']}")
            run = subprocess.run([
                "ansible-playbook", playbook,
                "-e", f"resource_id={inc['resource_id']}",
            ])

            if run.returncode == 0:
                mark_incident(inc["incident_id"], "auto_resolved")
                results.append({
                    "incident_id": inc["incident_id"],
                    "action": "auto_resolved",
                    "playbook": playbook,
                })
            else:
                print(f"{playbook} failed - escalating")
                mark_incident(inc["incident_id"], "escalated")
                results.append({
                    "incident_id": inc["incident_id"],
                    "action": "escalated",
                    "playbook": playbook,
                    "reason": "playbook failed",
                })

        return results


def auto_remediation_loop():
    while True:
        try:
            remediate_open_incidents(min_age_seconds=SETTLE_SECONDS)
        except Exception as error:
            print(f"Auto-remediation check failed: {error}")
        time.sleep(CHECK_INTERVAL)


@asynccontextmanager
async def lifespan(app):
    # Start the background loop when the service starts
    threading.Thread(target=auto_remediation_loop, daemon=True).start()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
def home():
    return {"message": "Remediation Service is running"}


@app.get("/check")
def check_incidents():
    incidents = requests.get(f"{CORRELATION_ENGINE}/incidents").json()
    print(f"Found {len(incidents)} open incident(s)")
    return incidents


@app.get("/remediate")
def remediate():
    # Manual trigger: act on open incidents right now, no waiting
    return remediate_open_incidents(min_age_seconds=0)