# BioNexus Development Roadmap

This document outlines the phased expansion of the BioNexus platform.

## Phase 1: Initial Project Bootstrap & Scaffolding (Current)
- [x] Monorepo structure (`frontend/`, `backend/`, `data/`, `docs/`)
- [x] Next.js + Tailwind CSS UI dashboard with placeholders
- [x] FastAPI backend with `/api/health` and `/api/compounds/search`
- [x] Environment variable configuration templates
- [x] Verification test suite & local development docs

---

## Phase 2: TiDB Cloud Persistence & Data Ingestion
- [ ] Connect TiDB Cloud via SQLAlchemy/PyMySQL with SSL support.
- [ ] Define database models:
  - `compounds` (ID, name, SMILES, formula, MW, source)
  - `proteins_genes` (UniProt ID, gene symbol, organism)
  - `pathways` (Reactome ID, pathway name, category)
  - `relationships` (source_id, target_id, relation_type, evidence_score, pmid)
- [ ] Build SDF parser for `streptomedb.sdf` and batch ingester with Pandas.

---

## Phase 3: Entity Resolution & Knowledge Graph Engine
- [ ] Implement entity resolution and synonym matching (PubChem, MeSH, ChEMBL).
- [ ] Construct in-memory/persisted Knowledge Graph using **NetworkX**.
- [ ] Graph centrality algorithms (Betweenness, PageRank) to identify key hub proteins.
- [ ] Subgraph extraction endpoints formatted for Cytoscape.js.

---

## Phase 4: Machine Learning & Bioactivity Prediction
- [ ] Extract molecular fingerprints (ECFP4 / Morgan fingerprints).
- [ ] Implement **scikit-learn** models for bioactivity classification and target affinity scoring.
- [ ] Rank predicted novel compound-target interactions with confidence metrics.

---

## Phase 5: LLM Grounded Explanations & Evidence Synthesis
- [ ] Connect LLM API (Google Gemini / OpenAI).
- [ ] Implement Retrieval-Augmented Generation (RAG) using graph subgraphs and literature PMIDs as ground truth.
- [ ] Enforce strict hallucination guardrails requiring every claim to cite a structured graph edge or PubMed PMID.

---

## Phase 6: Cytoscape.js Interactive Network Visualization
- [ ] Replace network placeholder with interactive WebGL/Canvas Cytoscape.js graph.
- [ ] Node filtering (compounds, proteins, pathways, diseases).
- [ ] Edge inspection displaying supporting evidence and affinity metrics.
