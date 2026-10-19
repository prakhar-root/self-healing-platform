#!/bin/bash
# Starts all three services in one terminal. Press Ctrl+C to stop them all.
cd "$(dirname "$0")"

if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
fi

mkdir -p logs

# Stop everything we started when this script exits (Ctrl+C)
trap 'echo; echo "Stopping all services..."; kill 0' EXIT

uvicorn correlation_engine:app --port 8001 > logs/correlation.log 2>&1 &
uvicorn alert_ingestion:app    --host 0.0.0.0 --port 8000 > logs/ingestion.log   2>&1 &
uvicorn remediation_service:app --port 8002 > logs/remediation.log 2>&1 &

# Wait until each service answers
for port in 8000 8001 8002; do
  for i in $(seq 1 30); do
    curl -s localhost:$port/ > /dev/null && break
    sleep 1
  done
done

echo "All services are running:"
echo "  Alert Ingestion      http://localhost:8000   (logs/ingestion.log)"
echo "  Correlation Engine   http://localhost:8001   (logs/correlation.log)"
echo "  Remediation Service  http://localhost:8002   (logs/remediation.log)"
echo "Press Ctrl+C to stop."
wait