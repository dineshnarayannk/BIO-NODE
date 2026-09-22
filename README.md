# BioNexus Monorepo

Welcome to the **BioNexus** codebase.

The full-stack application code, documentation, and data architecture are located in the [`bionexus/`](bionexus/) directory:

- [BioNexus Documentation & Setup Guide](bionexus/README.md)
- [Architecture Blueprint](bionexus/docs/architecture.md)
- [API Specification](bionexus/docs/api_specification.md)
- [Development Roadmap](bionexus/docs/roadmap.md)

### Quick Start

```bash
# 1. Start Backend
cd bionexus/backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# 2. Start Frontend
cd bionexus/frontend
npm run dev
```
