# BioNexus REST API Specification

Base URL: `http://localhost:8000/api` (or configured `NEXT_PUBLIC_API_BASE_URL`)

Interactive OpenAPI Docs: `http://localhost:8000/docs`

---

## Endpoints

### 1. Health Telemetry
**GET** `/api/health`

Confirms API availability and operational health.

**Response `200 OK`:**
```json
{
  "status": "ok",
  "service": "BioNexus API"
}
```

---

### 2. Compound Search
**GET** `/api/compounds/search?q={compound_query}`

Searches for natural compounds, secondary metabolites, or chemical identifiers.

**Query Parameters:**
| Parameter | Type | Required | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `q` | `string` | Yes | Compound name or search string (min length: 1) | `curcumin`, `capreomycin` |

**Response `200 OK` (Scaffold State):**
```json
{
  "query": "curcumin",
  "total_matches": 0,
  "items": [],
  "message": "Query received for 'curcumin'. Biological knowledge base indexing is initialized; data ingestion pending.",
  "metadata": {
    "source_status": "unindexed",
    "future_modules": [
      "streptomedb_ingestion",
      "networkx_graph",
      "tidb_persistence",
      "llm_grounding"
    ]
  }
}
```

**Response `422 Unprocessable Entity`:**
Occurs when query parameter `q` is missing or empty.

---

## Planned API Extensions

- **GET** `/api/compounds/{id}`: Detailed compound card (SMILES, 2D/3D structure, physicochemical properties).
- **GET** `/api/networks/subgraph?compound_id={id}`: NetworkX-derived subgraph JSON for Cytoscape.js rendering.
- **GET** `/api/evidence/citations?compound_id={id}`: PubMed PMIDs, clinical trials, and bioactivity assay tables.
- **POST** `/api/explanations/generate`: LLM-grounded mechanistic summary with citation backlinks.
