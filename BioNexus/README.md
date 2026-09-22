# BioNexus 🧬

> **Connecting Natural Compounds to Biological Insights**

BioNexus is an evidence-driven biological knowledge discovery platform that enables researchers, pharmacologists, and computational biologists to explore and unravel complex relationships between natural compounds, proteins, genes, pathways, and biological processes.

---

## 1. Project Purpose

Natural products synthesized by microorganisms and plants (such as secondary metabolites from *Streptomyces*) hold immense therapeutic potential. However, uncovering the mechanistic links between a natural compound, its target proteins, and downstream cellular pathways typically requires tedious manual literature searches and disconnected databases.

**BioNexus** bridges this gap by providing an end-to-end biological knowledge platform featuring:
- High-throughput compound exploration.
- Graph-based network analysis of compound-protein-pathway interactions.
- Relational storage of biological entities and relationships powered by **TiDB Cloud**.
- Rigorous evidence grounding with PubMed and clinical literature citations.
- AI-assisted mechanistic explanations grounded strictly in verified biological data.

---

## 2. Architecture & Data Flow

```
Frontend (Next.js 14 / TypeScript / Tailwind CSS)
   ↓
FastAPI Backend (/api/health, /api/compounds/search)
   ↓
SQLAlchemy 2.x ORM & PyMySQL Connection Pool
   ↓ (TLS/SSL Connection on Port 4000)
TiDB Cloud (Distributed MySQL Database)
```

---

## 3. Technology Stack

### Frontend
- **Framework**: Next.js 14+ (React 18+, TypeScript)
- **Styling**: Tailwind CSS & Modern Glassmorphism UI tokens
- **Icons**: Lucide React
- **Network Visuals (Future)**: Cytoscape.js for biological graph rendering

### Backend
- **Framework**: Python 3.10+ / FastAPI
- **ORM & Database Driver**: SQLAlchemy 2.x, PyMySQL, Cryptography
- **Validation**: Pydantic v2 & Pydantic-Settings
- **Server**: Uvicorn (ASGI)
- **Testing**: Pytest & Pytest-Asyncio

### Database & Relational Storage
- **Database**: **TiDB Cloud** (Distributed, scalable MySQL-compatible database with SSL/TLS connection support)
- **Entity Tables**:
  - `compounds`: Natural compound structures, SMILES, formulas, molecular weights, and identifiers.
  - `proteins`: Protein targets, enzymes, and receptors (UniProt).
  - `genes`: Gene entities encoding proteins (NCBI / Ensembl).
  - `pathways`: Biological signaling and metabolic pathways (Reactome / KEGG).
  - `biological_processes`: Cellular events and biological functions (Gene Ontology).
  - `relationships`: Central graph relationship table linking biological entities across domains.
  - `evidence`: Source database citations, PubMed PMIDs, and experimental confidence scores.

---

## 4. Directory Structure

```
bionexus/
├── frontend/             # Next.js TypeScript application & UI dashboard
│   ├── src/
│   │   ├── app/          # Next.js App Router (layout, page, styles)
│   │   ├── components/   # Modular React components (Header, Search, Placeholders)
│   │   ├── lib/          # API client and helper utilities
│   │   └── types/        # TypeScript interfaces
│   ├── .env.example      # Frontend environment template
│   └── package.json
├── backend/              # FastAPI Python service & database layer
│   ├── app/
│   │   ├── api/          # API router and endpoints (/health, /compounds)
│   │   ├── core/         # Settings, TiDB URL assembler, and SSL configs
│   │   ├── db/           # SQLAlchemy 2.x models, sessionmaker, and init_db
│   │   │   ├── models.py # 7 Core biological relational models
│   │   │   ├── session.py# Engine, get_db dependency, and connectivity test
│   │   │   └── init_db.py# Schema creation script (Base.metadata.create_all)
│   │   ├── schemas/      # Pydantic data validation models
│   │   └── main.py       # FastAPI application entrypoint with CORS
│   ├── tests/            # Automated Pytest suite (Unit & TiDB integration tests)
│   ├── .env.example      # Backend environment template (TiDB credentials)
│   └── requirements.txt
├── data/                 # Raw and processed biological datasets
│   ├── raw/              # Source files (SDF, TSV, CSV)
│   ├── processed/        # Extracted entities and knowledge graph indices
│   └── README.md
├── docs/                 # Architectural and technical documentation
│   ├── architecture.md   # Architectural blueprint & schema diagram
│   ├── api_specification.md # REST API endpoint contracts
│   └── roadmap.md        # Phased development plan
├── .gitignore            # Git ignore configuration
└── README.md             # Project documentation
```

---

## 5. How to Install & Configure

### Prerequisites
- **Node.js**: v18.0.0 or higher (`node -v`)
- **Python**: 3.10 or higher (`python3 --version`)

---

### Backend Installation & TiDB Configuration

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your **TiDB Cloud** credentials:
   ```env
   # Example TiDB Cloud configuration
   DB_HOST="gateway01.us-east-1.prod.aws.tidbcloud.com"
   DB_PORT=4000
   DB_USER="<YOUR_USER>.root"
   DB_PASSWORD="<YOUR_PASSWORD>"
   DB_NAME="bionexus"
   DB_SSL_VERIFY_CERT=True
   ```
5. Initialize database tables in TiDB:
   ```bash
   python -m app.db.init_db
   ```

---

### Frontend Installation

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Configure environment variables:
   ```bash
   cp .env.example .env.local
   ```

---

## 6. How to Run Locally

### Start Backend Service
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- API Health Endpoint: [http://localhost:8000/api/health](http://localhost:8000/api/health)
- Interactive OpenAPI Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### Start Frontend Application
```bash
cd frontend
npm run dev
```
- Web Application: [http://localhost:3000](http://localhost:3000)

---

## 7. Running Tests

Run the complete Pytest suite (isolated SQLite test environment with model and endpoint validation):
```bash
cd backend
source .venv/bin/activate
pytest -v
```

---

## 8. Current Functionality (Step 2 Complete)

- **Landing & Discovery Dashboard**: Clean, responsive, high-tech biology interface with dark mode theme.
- **Search System**: Natural compound search querying the `compounds` database table in real-time.
- **Live Health Telemetry**: `GET /api/health` validates both FastAPI application health and TiDB database connectivity.
- **7 Relational Database Models**: `compounds`, `proteins`, `genes`, `pathways`, `biological_processes`, `relationships`, `evidence`.
- **Modular Database Initializer**: `init_db.py` creates missing tables safely without dropping data.
