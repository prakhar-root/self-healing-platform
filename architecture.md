# Self-Healing Infrastructure Platform: Architecture (Draft)

## Problem
One failure (e.g. a container crash) triggers many related alerts, so
engineers get paged several times for the same root cause.

## Overall Flow
Prometheus detects a problem -> Alertmanager sends alerts as a webhook ->
Alert Ingestion Service receives them -> Correlation Engine groups related
alerts into one incident -> Remediation Service picks the fix -> Ansible
playbook performs the fix -> Grafana shows what happened.

## Data Model

### Alert
An alert is one small warning message from Prometheus.

| Field | Meaning | Example |
|---|---|---|
| alertname | What the problem is | HighCPU |
| resource_id | Which container it is about | order-service |
| severity | How bad it is | warning or critical |
| timestamp | When it happened | 10:15 AM |

### Incident
An incident is a group of related alerts about the same problem.

| Field | Meaning | Example |
|---|---|---|
| incident_id | A unique number for the incident | inc-001 |
| resource_id | Which container it is about | order-service |
| alerts | The list of alerts inside this incident | HighCPU, SlowResponse |
| severity | The worst severity among its alerts | critical |
| status | Where the incident stands | open, auto_resolved, or escalated |
| first_seen | When the first alert arrived | 10:15 AM |
| last_seen | When the latest alert arrived | 10:16 AM |

## Service Interfaces (who talks to whom)

The services talk to each other over HTTP. One service sends a request to
a URL on another service, and gets a reply.

| # | From | To | Request | What it does |
|---|---|---|---|---|
| 1 | Alertmanager | Alert Ingestion | POST /webhook/alert | Sends a new alert |
| 2 | Alert Ingestion | Correlation Engine | POST /alerts | Forwards the alert for grouping |
| 3 | Remediation Service | Correlation Engine | GET /incidents?status=open | Asks "what is currently broken?" |
| 4 | Remediation Service | Ansible | ansible-playbook (command) | Runs the fix for an incident |
| 5 | Remediation Service | Correlation Engine | POST /incidents/{id}/resolve | Marks the incident auto_resolved or escalated |

Replies:
- Correlation Engine replies to request 2 with the incident id and whether
  the alert was "merged" into an existing incident or a new one was "created".
- Correlation Engine replies to request 3 with the list of open incidents.

## Remediation Mapping (what gets fixed, and how)

This table is the "decision list" the Remediation Service uses: given an
incident, which Ansible playbook should run, and when should it give up
and escalate instead of retrying forever.

| # | Incident Type (what alertname it sees) | Ansible Playbook | Action | Escalate if... |
|---|---|---|---|---|
| 1 | Container crash / restart loop | restart_container.yml | Restart the container | Still crashing after 2 restart attempts |
| 2 | High CPU usage | scale_service.yml | Scale up (add one more replica) | Still high after scaling once |
| 3 | Service unresponsive / health check failing | restart_container.yml | Restart the container | Still failing after 2 attempts |
| 4 | Anything not in this table | (none) | No automatic fix | Escalate immediately |

Row 4 matters as much as the others — it's what makes this "self-healing
where possible, safe otherwise" instead of pretending to fix everything.

## Correlation Rules (in plain English)

These are the exact rules the Correlation Engine follows when a new alert
arrives:

1. Look at all currently open incidents.
2. For each one, check three things: is it about the same resource_id?
   Is its status still "open"? Did its last alert arrive within the last
   5 minutes?
3. If all three are true for any incident, add this new alert to that
   incident instead of creating a new one. Update its "last_seen" time.
   If the new alert's severity is worse, update the incident's severity
   to match the worse one.
4. If no incident matches, create a brand new incident with this one
   alert.
5. Duplicate alerts (the exact same alertname repeating for the same
   resource) just refresh "last_seen" — they don't add a second copy to
   the alerts list.

That 5-minute window and "same resource_id" rule are the two decisions
that do all the work. Everything else in the Correlation Engine is just
bookkeeping around these rules.

## Why These Tools (technology choices)

- **Rule-based correlation, not machine learning**: interpretable,
  needs no training data, and can be built and verified within the
  16-week timeframe.
- **Ansible for remediation**: idempotent (safe to re-run), and matches
  a tool already known, rather than writing raw Docker/Kubernetes API
  calls in Python.
- **Jenkins + Kubernetes**: current industry-standard tools for
  automating build, test, and deployment of containerized services.
- **Prometheus + Grafana**: already used in production monitoring
  (including at work), so alert format and dashboarding are familiar.

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









