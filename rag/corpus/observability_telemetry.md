# Network Observability and Streaming Telemetry

Traditional SNMP polling samples device state at coarse intervals and scales poorly. Model-driven
streaming telemetry instead pushes structured operational data (YANG-modeled) from devices to a
collector continuously, enabling sub-second visibility into interface counters, queue depths,
control-plane health, and environmental sensors.

A modern observability pipeline ingests telemetry (gRPC/gNMI dial-out, or Kafka), stores it in a
time-series database (e.g., Prometheus or InfluxDB), and visualizes/alerts on it (Grafana,
Alertmanager). The three pillars are metrics, logs, and traces; correlating them is what turns
raw data into root-cause insight.

Self-healing / closed-loop automation: when telemetry crosses a defined threshold or matches an
anomaly signature, an event triggers an automated remediation workflow (for example, re-route
around a degraded link, restart a process, or open a ticket with full context). This closes the
loop from detection to remediation without human intervention for known conditions.

Reliability impact: proactive detection of optical degradation, microbursts, and config drift
lets teams fix issues before they cause outages, which is how observability programs drive large
reductions in operational faults and mean-time-to-repair.
