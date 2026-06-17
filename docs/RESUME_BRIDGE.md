# Resume Bridge — what this project lets you legitimately claim

You chose the **grounded** path: only say what you can defend in an interview. Once you have
**run this project, understand the code, and pushed it to a public repo (e.g., GitHub)**, the
following becomes true and defensible. Don't claim it before you've actually done that.

---

## Draft resume bullets (grounded)

Add a new section — **"Selected AI Engineering Project"** or **"Independent AI Orchestration Work"** —
so a recruiter sees hands-on MCP/RAG immediately, separate from your infra-architect history.

> **AI Orchestration for Network Infrastructure** — *open-source project* · Python, MCP, ChromaDB
>
> - Built and open-sourced a **Model Context Protocol (MCP)** server (official Python SDK) exposing a
>   network-automation toolset — device inventory, interface state, fleet-wide config search, health
>   diagnostics, and LLDP topology — to **LLM agents** over stdio, enabling natural-language
>   troubleshooting of a spine-leaf / AI-fabric data center.
> - Implemented a **Retrieval-Augmented Generation (RAG)** pipeline over a networking knowledge corpus:
>   paragraph-aware chunking, **MiniLM sentence-embeddings**, a **ChromaDB vector database**, cosine
>   **semantic search**, and citation-enforced, anti-hallucination prompt assembly with an optional
>   LLM generation step.
> - Designed pluggable embedders and vector stores behind a single backend **abstraction layer**
>   (one swap-point fronting Cisco NSO RESTCONF / ACI APIC / NDFC / gNMI), keeping the agent
>   backend-agnostic and the tool surface stable from mock to production.

You can also fold one line into your **Cisco** experience, truthfully:
> - Extending API-driven network automation toward **agentic AI orchestration** — prototyping an MCP
>   tool layer that exposes fabric operations (NSO/RESTCONF) to LLM agents.

And tighten the **summary/skills** to add, only now that they're real: *Model Context Protocol (MCP),
Retrieval-Augmented Generation (RAG), vector databases (ChromaDB), embeddings & semantic search,
LLM tool-calling / agent integration, prompt engineering.*

---

## Interview talking points (be ready to defend each line)

- **"What is MCP and why use it?"** Open standard for connecting LLMs to tools/data; it decouples the
  model from heterogeneous device APIs so one agent works across NSO, APIC, NDFC. Point to your
  `_load_inventory()` swap-point as the abstraction boundary.
- **"Walk me through your RAG pipeline."** Chunk → embed (MiniLM) → store in ChromaDB → cosine
  nearest-neighbor retrieval → assemble a grounded prompt that forces citations → optional generate.
  Explain why you retrieve before you generate (grounding, reduced hallucination, source attribution).
- **"Why a vector database vs. keyword search?"** Embeddings capture semantic similarity, so
  *"training job stalls on one slow server"* retrieves the GPU-fabric straggler doc even with no shared
  keywords. You verified semantic retrieval beats your lexical-hash fallback on exactly this.
- **"How would this scale / go to production?"** Replace mock inventory with live RESTCONF/gNMI; add
  write-tools behind guardrails; add eval + observability on retrieval quality; cache embeddings.
- **Your real edge:** you already understand the *infrastructure* these systems run on (GPU/AI fabric,
  RoCEv2/MTU, BGP-EVPN) — most app-layer AI engineers don't. That domain grounding is the differentiator.

---

## Honest boundaries — do NOT claim yet
Reinforcement learning, model training/fine-tuning, transformer/neural-net development, computer
vision, knowledge graphs, multi-tier agent memory, semantic compression, "model capability
negotiation." None are in this project. Leave them off until you've built something real for them.

## Highest-value next builds (to deepen the claim)
1. **Agent loop** — a small script that lets an LLM call the MCP tools in a plan→act→observe loop to
   resolve a fault end-to-end (turns "exposed tools" into "autonomous agent").
2. **A second RAG source** — index real Cisco config guides or your own runbooks; add a reranker.
3. **Eval + observability** — measure retrieval precision and log tool-call traces (maps to the
   "AI observability / explainable AI" language honestly).
