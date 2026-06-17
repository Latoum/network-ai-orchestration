# Network Automation with NSO, RESTCONF, and Ansible

Cisco NSO (Network Services Orchestrator) is a model-driven orchestration platform. Services are
defined in YANG models; NSO renders the intended configuration to devices through NEDs (Network
Element Drivers) and maintains a transactional, rollback-capable view of network state. This
makes multi-device changes atomic: either the whole service deploys or it rolls back.

RESTCONF and NETCONF are the programmatic interfaces to modern devices. RESTCONF exposes YANG
data over HTTP verbs (GET/POST/PATCH/DELETE) with JSON or XML payloads; NETCONF uses SSH and
supports candidate configurations and explicit commit/confirmed-commit. Both replace screen-
scraping CLI with structured, schema-validated data.

Infrastructure-as-Code pattern: store intended state in version control, render device configs
from templates (Jinja2) or YANG service models, and apply through an idempotent engine (NSO,
Ansible, or Terraform). Idempotency means re-running the automation converges to the same state
without side effects, which is what makes large fleets manageable.

Operational benefit: standardized, API-driven workflows reduce manual variation and configuration
drift, shrink change windows, and make every change auditable. A single service request can fan
out to hundreds of coordinated API calls across many devices.
