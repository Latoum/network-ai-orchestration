# Network AI Orchestration — MCP + RAG over a Data-Center Fabric

A runnable portfolio project that implements an AI-orchestration layer grounded in a real domain: a spine-leaf / AI-factory data-center fabric.

It has two independent, working pieces. The first, mcp_server/, is a Model Context Protocol (MCP) server built on the official Python SDK that exposes network-automation tools (list devices, interface status, config search, diagnostics, topology) to any LLM agent. The second, rag/, is a Retrieval-Augmented Generation pipeline: chunking, sentence embeddings, a ChromaDB vector store, semantic search, and grounded, citation-enforced prompt assembly.

Both run with zero infrastructure (mock device inventory plus a local corpus), so the orchestration patterns can be demoed without touching production gear.

Full quickstart, configuration, and an honest "what this does and does not claim" mapping are included in the repository files.
