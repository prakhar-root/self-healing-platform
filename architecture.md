# Self-Healing Infrastructure Platform: Architecture (Draft)

## Problem
One failure (e.g. a container crash) triggers many related alerts, so
engineers get paged several times for the same root cause.

## Overall Flow
Prometheus detects a problem -> Alertmanager sends alerts as a webhook ->
Alert Ingestion Service receives them -> Correlation Engine groups related
alerts into one incident -> Remediation Service picks the fix -> Ansible
playbook performs the fix -> Grafana shows what happened.

## Service 1: Alert Ingestion
- Purpose: receive alerts from Alertmanager
- Input: JSON alert (alert name, resource id, severity)
- Output: passes the alert to the Correlation Engine

## Service 2: Correlation Engine
- Purpose: decide whether a new alert belongs to an existing incident
- Rule: same resource + incident still open + within last 5 minutes
  -> merge; otherwise create a new incident
- Input: alert
- Output: incident (id, resource, list of alerts, severity, status)

## Service 3: Remediation Service
- Purpose: fix known problems automatically
- Input: open incidents
- Action: run the matching Ansible playbook (e.g. restart container)
- If no playbook matches or the fix fails: mark incident as "escalated"

## Supporting Tools
- Prometheus + Alertmanager: detection and alert routing
- Ansible: executes the fix
- Docker / Kubernetes: where everything runs
- Jenkins: builds and deploys the services
- Grafana: dashboards (alerts vs incidents vs auto-resolved)

## Example Scenario
1. A container crashes
2. Prometheus fires 3 alerts (High CPU, Health check failed, Slow response)
3. Correlation Engine merges them into 1 incident
4. Remediation Service runs the restart playbook
5. Incident marked auto-resolved; Grafana shows it