# Cisco ACI Application-Centric Fabric

Cisco ACI (Application Centric Infrastructure) is an SDN fabric controlled by the APIC
(Application Policy Infrastructure Controller). The APIC is the single point of policy and
automation; it exposes a full REST API and object model (the MIT, Managed Information Tree),
which makes ACI well suited to Infrastructure-as-Code and programmatic orchestration.

Core policy objects: a Tenant is the top-level container; within it, a VRF provides a routing
instance, Bridge Domains define L2 flood boundaries, and EPGs (Endpoint Groups) group workloads
with common policy. Contracts define which EPGs may communicate and on which ports/protocols,
implementing an allow-list, zero-trust segmentation model.

ACI Multi-Site Orchestrator (now Nexus Dashboard Orchestrator) stretches policy across multiple
fabrics/sites for disaster recovery and workload mobility, while keeping each site's APIC cluster
as an independent failure domain.

Migration pattern: when moving from a traditional Nexus/STP network to ACI, use a "network-centric"
deployment first (one EPG per VLAN, mirroring the old topology) to de-risk the cutover, then
progressively refactor toward an "application-centric" model with granular contracts once the
application dependencies are mapped.

Automation: because every action is an API call against the APIC, ACI fabrics are commonly driven
by Python, Ansible (cisco.aci collection), or Terraform, enabling repeatable, version-controlled
deployments instead of box-by-box CLI configuration.
