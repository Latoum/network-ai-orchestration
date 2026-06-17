# Network AI Orchestration — MCP + RAG over a Data-Center Fabric

A small, runnable portfolio project that implements the **AI-orchestration layer** the way the
"Cross-Architecture Cloud Technical Lead — AI Orchestration" role describes it — but grounded in a
real domain: a spine-leaf / AI-factory data-center fabric.

It has two independent, working pieces:

1. **`mcp_server/`** — a **Model Context Protocol (MCP)** server (official Python SDK) that exposes
   network-automation tools to any LLM agent (Claude Desktop, IDE assistants, custom agents).
2. **`rag/`** — a **Retrieval-Augmented Generation (RAG)** pipeline: chunking → **embeddings** →
   **ChromaDB vector database** → **semantic search** → grounded prompt assembly → optional LLM answer.

> Both run with **zero infrastructure** (mock device inventory + local corpus) so you can demo the
> orchestration patterns without touching production gear.

---

## What this demonstrates (and maps to the role)

| Role language | Where it lives in this repo |
|---|---|
| **Model Context Protocol (MCP)** | `mcp_server/network_mcp_server.py` — `FastMCP` server, 6 tools, stdio transport |
| **AI agents orchestrating API functions** | the tool surface (`list_devices`, `get_interface_status`, `search_configs`, `run_diagnostic`, `get_topology`, `get_device`) an LLM invokes autonomously |
| **Abstraction layer over multi-platform infrastructure** | `_load_inventory()` — the single swap-point that fronts NSO RESTCONF / ACI APIC / NDFC / gNMI behind one interface |
| **Retrieval-Augmented Generation (RAG)** | `rag/rag_pipeline.py` (ingest → retrieve → assemble → generate) |
| **Vector databases** | ChromaDB persistent client (cosine space) |
| **Embedding models / semantic search** | MiniLM (`all-MiniLM-L6-v2`) sentence-embeddings + nearest-neighbor retrieval |
| **LLM integration / prompt engineering** | `build_prompt()` (grounded, citation-enforced, anti-hallucination) + `maybe_generate()` |
| **AI/MLOps pipeline & workflow orchestration** | pluggable embedders + vector stores, with graceful fallback, behind a single CLI pipeline |

### Deliberately *not* claimed here (would be overclaiming)
This repo does **not** implement reinforcement learning, model fine-tuning/training, transformer
architecture work, computer vision, knowledge graphs, multi-tier agent memory, or semantic
compression. Those appear in the job text but are out of scope for this project — see
`docs/RESUME_BRIDGE.md` for an honest boundary of what to claim and what to build next.

---

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 1) RAG pipeline
```bash
cd rag
python rag_pipeline.py ingest --reset                  # builds the ChromaDB index (downloads the
                                                       # MiniLM model on first run; needs internet)
python rag_pipeline.py search "why did my VXLAN tunnel break after a change"
python rag_pipeline.py ask    "how do I avoid a full iBGP mesh in an EVPN fabric"
```
Fully offline (air-gapped / no model download, no ChromaDB):
```bash
python rag_pipeline.py ingest --reset --embedder hash --store numpy
python rag_pipeline.py search "lossless GPU fabric MTU" --embedder hash --store numpy
```
Generated answers (the "G" in RAG) are optional and only run if a key is set:
```bash
pip install anthropic && export ANTHROPIC_API_KEY=...   # otherwise `ask` prints the assembled RAG prompt
```

### 2) MCP server
```bash
cd mcp_server
python network_mcp_server.py        # speaks MCP over stdio
```
Register it with **Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "network-automation": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_server/network_mcp_server.py"]
    }
  }
}
```
Then ask Claude things like *"run a diagnostic on leaf-02 and tell me what's wrong"* — it will call
`run_diagnostic` and reason over the structured result (the seeded fabric has a real fault to find).

---

## From mock to production
- **MCP tools:** replace the body of `_load_inventory()` with live API calls (NSO RESTCONF, APIC REST,
  NDFC, or gNMI/gNMI-dial-out telemetry). The tool signatures stay identical, so the agent is unchanged.
  All tools are **read-only** by design; add write tools only behind explicit guardrails.
- **RAG corpus:** drop your own `.md`/`.txt` docs into `rag/corpus/` and re-run `ingest`.
- **Store location:** set `RAG_STORE_DIR` to a local-disk path if you run on a network/overlay
  filesystem (ChromaDB's SQLite backend needs normal file-locking/mmap).

## Status
Verified working: MCP server (all 6 tools + diagnostics) and the RAG pipeline end-to-end through the
real ChromaDB vector database. The MiniLM model downloads on first run; use `--embedder hash` for a
fully offline demo.
