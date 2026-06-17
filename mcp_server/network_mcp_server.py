#!/usr/bin/env python3
"""
Network Automation MCP Server
=============================

A Model Context Protocol (MCP) server that exposes a set of *network-automation tools*
to any MCP-capable LLM client (Claude Desktop, IDE assistants, custom agents).

WHY THIS MATTERS
----------------
MCP is the open standard for connecting LLM agents to external tools and data. Each function
decorated with ``@mcp.tool()`` below becomes a callable "tool" that an LLM can invoke
autonomously to reason about, query, and troubleshoot a network fabric in natural language.
This is the "AI agent orchestrating API functions over multi-platform infrastructure" pattern,
implemented for a real domain: a spine-leaf / AI-fabric data center.

The tools here read from a mock inventory (``inventory.json``) so the server runs with zero
infrastructure. Every data-access call is isolated in ``_load_inventory()`` -- the single
SWAP POINT where you connect real device APIs (Cisco NSO RESTCONF, ACI APIC REST, NDFC, gNMI).
All tools are strictly READ-ONLY by design.

RUN
---
    pip install mcp
    python network_mcp_server.py          # stdio transport (for Claude Desktop / MCP clients)

REGISTER WITH CLAUDE DESKTOP (claude_desktop_config.json)
---------------------------------------------------------
    {
      "mcpServers": {
        "network-automation": {
          "command": "python",
          "args": ["/absolute/path/to/network_mcp_server.py"]
        }
      }
    }
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

INVENTORY_PATH = Path(__file__).with_name("inventory.json")

mcp = FastMCP(
    "network-automation",
    instructions=(
        "Tools to inspect and troubleshoot a spine-leaf / AI data-center fabric. "
        "Use list_devices/get_topology to orient, get_interface_status and search_configs "
        "to inspect detail, and run_diagnostic for a health verdict on a device. All read-only."
    ),
)


# --------------------------------------------------------------------------------------
# SWAP POINT -- replace the file read below with live calls to your source(s) of truth:
#   Cisco NSO : GET {nso}/restconf/data/tailf-ncs:devices
#   ACI APIC  : GET {apic}/api/node/class/topSystem.json   (X-Auth token)
#   NDFC/DCNM : GET {ndfc}/appcenter/cisco/ndfc/api/v1/lan-fabric/.../inventory/switches
#   gNMI/gNOI : streaming telemetry subscription -> cache -> serve here
# Keeping all I/O behind this one function is what makes the agent backend-agnostic.
# --------------------------------------------------------------------------------------
def _load_inventory() -> dict:
    with open(INVENTORY_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _device_index() -> dict[str, dict]:
    return {d["hostname"]: d for d in _load_inventory()["devices"]}


@mcp.tool()
def list_devices(role: Optional[str] = None) -> list[dict]:
    """List devices in the fabric, optionally filtered by role.

    Args:
        role: Optional role filter -- one of 'spine', 'leaf', 'border'. Omit for all devices.

    Returns:
        A list of {hostname, mgmt_ip, model, os, role, site} records.
    """
    devices = _load_inventory()["devices"]
    if role:
        devices = [d for d in devices if d["role"].lower() == role.lower()]
    return [
        {k: d[k] for k in ("hostname", "mgmt_ip", "model", "os", "role", "site")}
        for d in devices
    ]


@mcp.tool()
def get_device(hostname: str) -> dict:
    """Return the full inventory record for a single device (interfaces, BGP, LLDP, env, config).

    Args:
        hostname: Device hostname, e.g. 'leaf-02'.
    """
    idx = _device_index()
    if hostname not in idx:
        return {"error": f"unknown device '{hostname}'", "known_devices": sorted(idx)}
    return idx[hostname]


@mcp.tool()
def get_interface_status(hostname: str, interface: Optional[str] = None) -> dict:
    """Return operational status and error counters for interfaces on a device.

    Args:
        hostname: Device hostname, e.g. 'leaf-02'.
        interface: Optional specific interface name, e.g. 'Eth1/50'. Omit for all interfaces.
    """
    idx = _device_index()
    if hostname not in idx:
        return {"error": f"unknown device '{hostname}'", "known_devices": sorted(idx)}
    ifaces = idx[hostname]["interfaces"]
    if interface:
        match = [i for i in ifaces if i["name"].lower() == interface.lower()]
        if not match:
            return {"error": f"no interface '{interface}' on {hostname}",
                    "known_interfaces": [i["name"] for i in ifaces]}
        return {"hostname": hostname, "interface": match[0]}
    return {"hostname": hostname, "interfaces": ifaces}


@mcp.tool()
def search_configs(query: str) -> list[dict]:
    """Full-text search every device's running-config for a string.

    Useful for fleet-wide questions like 'which devices set jumbo MTU?' or
    'find any interface still on mtu 1500'.

    Args:
        query: Case-insensitive substring to search for, e.g. 'anycast-gateway' or 'mtu 9216'.
    """
    q = query.lower()
    hits: list[dict] = []
    for d in _load_inventory()["devices"]:
        for lineno, line in enumerate(d.get("running_config", []), start=1):
            if q in line.lower():
                hits.append({"hostname": d["hostname"], "line": lineno, "config": line})
    return hits


@mcp.tool()
def run_diagnostic(hostname: str) -> dict:
    """Run a read-only health check on a device and return a structured verdict.

    Evaluates interface error counters, admin/oper mismatches, MTU consistency on fabric
    uplinks, BGP neighbor adjacencies, and environmental alarms.

    Args:
        hostname: Device hostname, e.g. 'leaf-02'.

    Returns:
        {hostname, status: ok|degraded|critical, findings: [...], checked_at}.
    """
    idx = _device_index()
    if hostname not in idx:
        return {"error": f"unknown device '{hostname}'", "known_devices": sorted(idx)}
    d = idx[hostname]
    findings: list[str] = []

    for i in d["interfaces"]:
        if i["admin"] == "up" and i["oper"] != "up":
            findings.append(f"{i['name']} admin-up but oper-{i['oper']} ({i['desc']})")
        if i.get("in_errors", 0) > 1000 or i.get("out_errors", 0) > 1000:
            findings.append(f"{i['name']} high error counters "
                            f"(in={i['in_errors']}, out={i['out_errors']})")
        if i["desc"].lower().find("rocev2") >= 0 and i.get("mtu", 0) < 9216:
            findings.append(f"{i['name']} RoCEv2 link on mtu {i['mtu']} "
                            f"(expect jumbo 9216 for lossless GPU fabric)")

    for n in d.get("bgp_neighbors", []):
        if n["state"] != "Established":
            findings.append(f"BGP neighbor {n['peer']} ({n['afi']}) is {n['state']}")

    for sensor, val in d.get("env", {}).items():
        if val != "ok":
            findings.append(f"environment: {sensor} = {val}")

    if any("oper-down" in f or "Idle" in f or "critical" in f for f in findings):
        status = "critical"
    elif findings:
        status = "degraded"
    else:
        status = "ok"

    return {
        "hostname": hostname,
        "status": status,
        "findings": findings or ["no issues detected"],
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@mcp.tool()
def get_topology() -> dict:
    """Return fabric adjacency (leaf/border uplinks to spines) derived from LLDP neighbors."""
    inv = _load_inventory()
    edges = []
    for d in inv["devices"]:
        for peer in d.get("lldp", []):
            edges.append({"a": d["hostname"], "b": peer})
    # de-duplicate undirected edges
    seen, uniq = set(), []
    for e in edges:
        key = tuple(sorted((e["a"], e["b"])))
        if key not in seen:
            seen.add(key)
            uniq.append({"a": key[0], "b": key[1]})
    return {"fabric": inv["fabric"], "site": inv["site"], "adjacencies": uniq}


@mcp.resource("network://inventory")
def inventory_resource() -> str:
    """The raw fabric inventory as a JSON resource the model can read for broad context."""
    return json.dumps(_load_inventory(), indent=2)


if __name__ == "__main__":
    # Default transport is stdio -- the transport MCP clients like Claude Desktop expect.
    mcp.run()
