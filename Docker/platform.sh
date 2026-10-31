#!/bin/bash
# Runs the three services as containers on one network.
# Stop the local copies first (Ctrl+C on start_all.sh) so ports 8000-8002 are free.

docker rm -f correlation-engine alert-ingestion remediation-service > /dev/null 2>&1
docker network create platform-net > /dev/null 2>&1

docker run -d --name correlation-engine --network platform-net --restart unless-stopped \
  -p 8001:8001 \
  self-healing/correlation-engine:latest

docker run -d --name alert-ingestion --network platform-net --restart unless-stopped \
  -e CORRELATION_ENGINE=http://correlation-engine:8001 \
  -p 8000:8000 \
  self-healing/alert-ingestion:latest

# The Docker socket lets this container restart other containers
docker run -d --name remediation-service --network platform-net --restart unless-stopped \
  -e CORRELATION_ENGINE=http://correlation-engine:8001 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -p 8002:8002 \
  self-healing/remediation-service:latest

echo
echo "Platform started:"
echo "  Alert Ingestion      http://localhost:8000"
echo "  Correlation Engine   http://localhost:8001"
echo "  Remediation Service  http://localhost:8002"
docker ps --filter name=correlation-engine --filter name=alert-ingestion --filter name=remediation-service --format "table {{.Names}}\t{{.Status}}"