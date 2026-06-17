#!/usr/bin/env python3
"""
RAG Pipeline over Networking Knowledge
======================================

A self-contained Retrieval-Augmented Generation (RAG) pipeline that indexes a corpus of
networking reference docs into a vector database, performs semantic search, and assembles
grounded, citation-ready context for an LLM.

Demonstrates, end to end:
  * chunking + embeddings (vectorization of text)
  * a vector database (ChromaDB) for storage + approximate nearest-neighbor semantic search
  * retrieval + context assembly (the "R" and "A" of RAG)
  * an optional LLM generation step (the "G"), used only if an API key is present

DESIGN: both the embedder and the vector store are pluggable.
  - Embedder:  'minilm'  -> sentence-transformers all-MiniLM-L6-v2 (semantic; production path)
               'hash'    -> deterministic char-n-gram hashing (offline; tests/CI/fallback)
  - Store:     'chroma'  -> ChromaDB persistent vector database (production path)
               'numpy'   -> in-memory cosine store (fallback if chromadb is unavailable)
The pipeline degrades gracefully: if a semantic dependency is missing it warns and falls back,
so the demo always runs.

USAGE
-----
    pip install -r ../requirements.txt
    python rag_pipeline.py ingest --reset
    python rag_pipeline.py search "why did my VXLAN tunnel break"
    python rag_pipeline.py ask    "how do I avoid an iBGP full mesh in an EVPN fabric"

    # fully offline (no model download, no chromadb):
    python rag_pipeline.py ingest --reset --embedder hash --store numpy
    python rag_pipeline.py search "lossless GPU fabric MTU" --embedder hash --store numpy

To enable real generated answers in `ask`:  pip install anthropic && export ANTHROPIC_API_KEY=...
"""
from __future__ import annotations

import argparse
import hashlib
import math
import os
import re
import sys
from pathlib import Path
from typing import Sequence

CORPUS_DIR = Path(__file__).with_name("corpus")
# Redirect with RAG_STORE_DIR if the default path is on a network/overlay filesystem that
# lacks SQLite file-locking / mmap support (ChromaDB needs a normal local disk).
STORE_DIR = Path(os.environ.get("RAG_STORE_DIR", str(Path(__file__).with_name("chroma_store"))))
COLLECTION = "netdocs"


# ======================================================================================
# Embedders
# ======================================================================================
class HashEmbedder:
    """Deterministic, dependency-free embedding via char/word n-gram hashing.

    Not semantic-grade, but requires no model download -- used for CI/tests and as a
    graceful fallback so the pipeline always runs offline.
    """

    name = "hash"

    def __init__(self, dim: int = 256):
        self.dim = dim

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for t in texts:
            vec = [0.0] * self.dim
            low = t.lower()
            tokens = re.findall(r"[a-z0-9]+", low)
            trigrams = [low[i:i + 3] for i in range(max(0, len(low) - 2))]
            for gram in tokens + trigrams:
                h = int(hashlib.md5(gram.encode("utf-8")).hexdigest(), 16)
                vec[h % self.dim] += 1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            out.append([v / norm for v in vec])
        return out


class MiniLMEmbedder:
    """Real semantic embeddings (~384-dim). Production path.

    Prefers sentence-transformers all-MiniLM-L6-v2; if that is not installed, falls back to
    chromadb's bundled ONNX DefaultEmbeddingFunction (same model family, no torch needed).
    """

    name = "minilm"

    def __init__(self):
        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer("all-MiniLM-L6-v2")
            self._encode = lambda texts: [list(map(float, v)) for v in model.encode(list(texts))]
        except Exception:
            from chromadb.utils import embedding_functions

            ef = embedding_functions.DefaultEmbeddingFunction()
            self._encode = lambda texts: [list(map(float, v)) for v in ef(list(texts))]

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return self._encode(list(texts))


def make_embedder(name: str):
    if name == "minilm":
        try:
            return MiniLMEmbedder()
        except Exception as exc:  # pragma: no cover - depends on environment
            print(f"[warn] semantic embedder unavailable ({exc}); falling back to 'hash'",
                  file=sys.stderr)
            return HashEmbedder()
    return HashEmbedder()


# ======================================================================================
# Vector stores
# ======================================================================================
class ChromaStore:
    """ChromaDB persistent vector database (cosine space). Production path."""

    name = "chroma"

    def __init__(self, reset: bool = False):
        import chromadb

        self.client = chromadb.PersistentClient(path=str(STORE_DIR))
        if reset:
            try:
                self.client.delete_collection(COLLECTION)
            except Exception:
                pass
        self.col = self.client.get_or_create_collection(
            COLLECTION, metadata={"hnsw:space": "cosine"}
        )

    def add(self, ids, embeddings, documents, metadatas):
        self.col.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)

    def query(self, embedding, k):
        res = self.col.query(
            query_embeddings=[embedding], n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        hits = []
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            hits.append({"document": doc, "metadata": meta, "score": 1.0 - float(dist)})
        return hits

    def count(self):
        return self.col.count()


class NumpyStore:
    """In-memory cosine store with pickle persistence. Fallback when chromadb is unavailable."""

    name = "numpy"

    def __init__(self, reset: bool = False):
        import pickle

        self._pickle = pickle
        STORE_DIR.mkdir(parents=True, exist_ok=True)
        self.path = STORE_DIR / "numpy_store.pkl"
        self.ids, self.docs, self.metas, self.vecs = [], [], [], None
        if reset and self.path.exists():
            try:
                self.path.unlink()
            except OSError:
                pass  # some filesystems forbid unlink; add() will overwrite
        if not reset and self.path.exists():
            data = pickle.load(open(self.path, "rb"))
            self.ids, self.docs, self.metas, self.vecs = (
                data["ids"], data["docs"], data["metas"], data["vecs"])

    def add(self, ids, embeddings, documents, metadatas):
        import numpy as np

        arr = np.asarray(embeddings, dtype="float32")
        self.vecs = arr if self.vecs is None else np.vstack([self.vecs, arr])
        self.ids += list(ids)
        self.docs += list(documents)
        self.metas += list(metadatas)
        self._pickle.dump(
            {"ids": self.ids, "docs": self.docs, "metas": self.metas, "vecs": self.vecs},
            open(self.path, "wb"),
        )

    def query(self, embedding, k):
        import numpy as np

        q = np.asarray(embedding, dtype="float32")
        q = q / (np.linalg.norm(q) or 1.0)
        vn = self.vecs / (np.linalg.norm(self.vecs, axis=1, keepdims=True) + 1e-9)
        sims = vn @ q
        order = np.argsort(-sims)[:k]
        return [{"document": self.docs[i], "metadata": self.metas[i], "score": float(sims[i])}
                for i in order]

    def count(self):
        return len(self.ids)


def make_store(name: str, reset: bool = False):
    if name == "chroma":
        try:
            return ChromaStore(reset=reset)
        except Exception as exc:
            print(f"[warn] chromadb unavailable ({exc}); falling back to 'numpy' store",
                  file=sys.stderr)
            return NumpyStore(reset=reset)
    return NumpyStore(reset=reset)


# ======================================================================================
# Pipeline
# ======================================================================================
def chunk_text(text: str, max_chars: int = 700) -> list[str]:
    """Paragraph-aware chunking: greedily pack paragraphs up to ~max_chars."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, cur = [], ""
    for p in paras:
        if cur and len(cur) + len(p) + 2 > max_chars:
            chunks.append(cur)
            cur = p
        else:
            cur = f"{cur}\n\n{p}".strip()
    if cur:
        chunks.append(cur)
    return chunks


def ingest(embedder, store) -> tuple[int, int]:
    files = sorted(CORPUS_DIR.glob("*.md")) + sorted(CORPUS_DIR.glob("*.txt"))
    ids, docs, metas = [], [], []
    for f in files:
        for i, ch in enumerate(chunk_text(f.read_text(encoding="utf-8"))):
            ids.append(f"{f.stem}::{i}")
            docs.append(ch)
            metas.append({"source": f.name, "chunk": i})
    if not docs:
        raise SystemExit(f"no documents found in {CORPUS_DIR}")
    store.add(ids, embedder.embed(docs), docs, metas)
    return len(docs), len(files)


def search(embedder, store, query: str, k: int = 4):
    qv = embedder.embed([query])[0]
    return store.query(qv, k)


def build_prompt(query: str, hits) -> str:
    context = "\n\n".join(
        f"[{h['metadata']['source']} #{h['metadata']['chunk']}]\n{h['document']}" for h in hits
    )
    return (
        "You are a senior network engineering assistant. Answer the QUESTION using ONLY the "
        "CONTEXT below. Cite sources inline like [filename]. If the context is insufficient, "
        "say so plainly.\n\n"
        f"# CONTEXT\n{context}\n\n# QUESTION\n{query}\n\n# ANSWER\n"
    )


def maybe_generate(prompt: str):
    """Call an LLM only if ANTHROPIC_API_KEY is set; otherwise return None (offline mode)."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic

        client = anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-3-5-sonnet-latest", max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    except Exception as exc:  # pragma: no cover
        return f"(LLM generation skipped: {exc})"


# ======================================================================================
# CLI
# ======================================================================================
def _print_hits(hits):
    for rank, h in enumerate(hits, 1):
        m = h["metadata"]
        print(f"  {rank}. score={h['score']:.3f}  [{m['source']} #{m['chunk']}]")
        snippet = " ".join(h["document"].split())
        print(f"     {snippet[:160]}{'...' if len(snippet) > 160 else ''}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="RAG pipeline over networking docs.")
    ap.add_argument("command", choices=["ingest", "search", "ask"])
    ap.add_argument("query", nargs="*", help="query text for search/ask")
    ap.add_argument("--embedder", default="minilm", choices=["minilm", "hash"])
    ap.add_argument("--store", default="chroma", choices=["chroma", "numpy"])
    ap.add_argument("-k", type=int, default=4, help="number of chunks to retrieve")
    ap.add_argument("--reset", action="store_true", help="rebuild the index from scratch")
    args = ap.parse_args(argv)

    embedder = make_embedder(args.embedder)
    store = make_store(args.store, reset=args.reset)
    print(f"[info] embedder={embedder.name}  store={store.name}", file=sys.stderr)

    if args.command == "ingest":
        n_chunks, n_files = ingest(embedder, store)
        print(f"Indexed {n_chunks} chunks from {n_files} files into the '{store.name}' store "
              f"({store.count()} vectors total).")
        return

    query = " ".join(args.query).strip()
    if not query:
        raise SystemExit("provide a query, e.g.  python rag_pipeline.py search \"vxlan mtu\"")
    if store.count() == 0:
        raise SystemExit("index is empty -- run `ingest` first (same --embedder/--store).")

    hits = search(embedder, store, query, k=args.k)

    if args.command == "search":
        print(f"\nTop {len(hits)} results for: {query!r}\n")
        _print_hits(hits)
        return

    # ask
    prompt = build_prompt(query, hits)
    answer = maybe_generate(prompt)
    print(f"\nQuestion: {query}\n")
    print("Retrieved context:")
    _print_hits(hits)
    print()
    if answer:
        print("Generated answer:\n" + answer)
    else:
        print("[offline] No ANTHROPIC_API_KEY set -- returning assembled RAG prompt instead of a\n"
              "generated answer. Set the key (and `pip install anthropic`) to enable generation.\n")
        print("----- assembled prompt -----")
        print(prompt)


if __name__ == "__main__":
    main()
