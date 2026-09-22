# BioNexus Data Directory

This directory stores biological datasets, molecular structure files, and processed knowledge graph artifacts.

## Directory Structure

```
data/
├── raw/                 # Unmodified raw source data (SDF, CSV, TSV, XML)
│   ├── streptomedb/     # StreptomeDB natural products from Streptomyces
│   ├── pubchem/         # PubChem compound records
│   ├── uniprot/         # Protein and target sequence data
│   └── pathway/         # KEGG, Reactome, GO pathway mappings
├── processed/           # Sanitized, resolved entities and graph indices
│   ├── entities/        # Normalized JSON/Parquet entity dictionaries
│   └── graphs/          # NetworkX / adjacency matrices & embeddings
└── README.md
```

## Data Sources

1. **StreptomeDB**: Natural compounds synthesized by *Streptomyces* strains, including capreomycin, actinomycin, and streptomycin derivatives (SDF formats).
2. **PubChem / ChEMBL**: Molecular formulas, SMILES, InChIKey, and target bioactivities.
3. **UniProt / STRING**: Protein targets, identifiers, and protein-protein interaction networks.
4. **Reactome / KEGG / Gene Ontology**: Biological pathways, biological processes, and cellular components.

## Data Governance & Large Files

- Large source files (`*.sdf`, `*.tar.gz`, `*.h5`) are excluded from Git via `.gitignore`.
- Keep lightweight metadata manifests or ETL scripts in `bionexus/backend/app/services/data_ingestion/` (future phase).
