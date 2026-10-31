#!/bin/bash
# Builds the three service images.
set -e

cd "$(dirname "$0")/.."

docker build -f Docker/corelation_file -t self-healing/correlation-engine:latest .
docker build -f Docker/ingestion_file -t self-healing/alert-ingestion:latest .
docker build -f Docker/remediation_file -t self-healing/remediation-service:latest .

echo "All three Docker images built successfully!"
