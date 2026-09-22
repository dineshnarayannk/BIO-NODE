"""Biological and Pathway Analysis service.

Generates qualitative biological interpretations, pathway mapping summaries,
and functional process connections from verified Reactome and Gene Ontology annotations.
Strictly avoids fabricating statistical p-values or enrichment scores.
"""

from collections import defaultdict
import logging
from typing import Dict, List, Set
from sqlalchemy import select
from sqlalchemy.orm import Session
from ...db.models import BiologicalProcess, Compound, Gene, Pathway, Protein, Relationship
from ...schemas.analysis import (
    BiologicalAnalysisResponse,
    BiologicalPathwaySummary,
    BiologicalProcessDetail,
)
from ...schemas.compound import CompoundSummary

logger = logging.getLogger("bionexus.analysis.biological")


def analyze_compound_biology(
    db: Session,
    compound: Compound,
) -> BiologicalAnalysisResponse:
    """Perform descriptive biological and pathway interpretation for a natural compound."""
    compound_summary = CompoundSummary(
        id=str(compound.id),
        name=compound.name,
        canonical_id=compound.canonical_id,
        pubchem_cid=compound.pubchem_cid,
        smiles=compound.smiles,
        molecular_weight=compound.molecular_weight,
        source=f"StreptomeDB (canonical_id: {compound.canonical_id})",
    )

    # 1. Target Proteins
    protein_rels = db.execute(
        select(Relationship).where(
            Relationship.source_type == "compound",
            Relationship.source_id == compound.id,
            Relationship.relationship_type == "targets",
            Relationship.target_type == "protein",
        )
    ).scalars().all()

    protein_ids = [rel.target_id for rel in protein_rels]
    proteins = []
    if protein_ids:
        proteins = db.execute(
            select(Protein).where(Protein.id.in_(protein_ids))
        ).scalars().all()
    protein_map = {p.id: p for p in proteins}

    # 2. Encoding Genes
    gene_rels = []
    if protein_ids:
        gene_rels = db.execute(
            select(Relationship).where(
                Relationship.source_type == "protein",
                Relationship.source_id.in_(protein_ids),
                Relationship.relationship_type == "encoded_by",
                Relationship.target_type == "gene",
            )
        ).scalars().all()

    gene_ids = [rel.target_id for rel in gene_rels]
    genes = []
    if gene_ids:
        genes = db.execute(
            select(Gene).where(Gene.id.in_(gene_ids))
        ).scalars().all()
    gene_map = {g.id: g for g in genes}

    # Map protein -> genes
    protein_to_genes: Dict[int, List[Gene]] = defaultdict(list)
    gene_to_proteins: Dict[int, List[Protein]] = defaultdict(list)
    for gr in gene_rels:
        p = protein_map.get(gr.source_id)
        g = gene_map.get(gr.target_id)
        if p and g:
            protein_to_genes[p.id].append(g)
            gene_to_proteins[g.id].append(p)

    # 3. Pathways
    pathway_rels = []
    if gene_ids:
        pathway_rels = db.execute(
            select(Relationship).where(
                Relationship.source_type == "gene",
                Relationship.source_id.in_(gene_ids),
                Relationship.relationship_type == "participates_in",
                Relationship.target_type == "pathway",
            )
        ).scalars().all()

    pathway_ids = [rel.target_id for rel in pathway_rels]
    pathways = []
    if pathway_ids:
        pathways = db.execute(
            select(Pathway).where(Pathway.id.in_(pathway_ids))
        ).scalars().all()
    pathway_map = {pw.id: pw for pw in pathways}

    pathway_genes: Dict[int, Set[str]] = defaultdict(set)
    pathway_proteins: Dict[int, Set[str]] = defaultdict(set)
    for pr in pathway_rels:
        g = gene_map.get(pr.source_id)
        pw = pathway_map.get(pr.target_id)
        if g and pw:
            pathway_genes[pw.id].add(g.canonical_id)
            for p in gene_to_proteins.get(g.id, []):
                pathway_proteins[pw.id].add(p.name)

    connected_pathways: List[BiologicalPathwaySummary] = []
    for pw in pathways:
        connected_pathways.append(
            BiologicalPathwaySummary(
                pathway_id=pw.id,
                canonical_id=pw.canonical_id,
                name=pw.name,
                mediating_genes=sorted(list(pathway_genes[pw.id])),
                mediating_proteins=sorted(list(pathway_proteins[pw.id])),
            )
        )

    # 4. Biological Processes
    bp_rels = []
    if gene_ids:
        bp_rels = db.execute(
            select(Relationship).where(
                Relationship.source_type == "gene",
                Relationship.source_id.in_(gene_ids),
                Relationship.relationship_type == "associated_with",
                Relationship.target_type == "biological_process",
            )
        ).scalars().all()

    bp_ids = [rel.target_id for rel in bp_rels]
    processes = []
    if bp_ids:
        processes = db.execute(
            select(BiologicalProcess).where(BiologicalProcess.id.in_(bp_ids))
        ).scalars().all()
    bp_map = {bp.id: bp for bp in processes}

    bp_genes: Dict[int, Set[str]] = defaultdict(set)
    for bpr in bp_rels:
        g = gene_map.get(bpr.source_id)
        bp = bp_map.get(bpr.target_id)
        if g and bp:
            bp_genes[bp.id].add(g.canonical_id)

    connected_processes: List[BiologicalProcessDetail] = []
    for bp in processes:
        connected_processes.append(
            BiologicalProcessDetail(
                process_id=bp.id,
                canonical_id=bp.canonical_id,
                name=bp.name,
                mediating_genes=sorted(list(bp_genes[bp.id])),
            )
        )

    # 5. Convergence analysis
    pathway_convergence = [
        f"{pw.name} ({pw.canonical_id}) is linked through {len(pathway_genes[pw.id])} gene(s): {', '.join(sorted(pathway_genes[pw.id]))}"
        for pw in pathways
        if len(pathway_genes[pw.id]) >= 1
    ]

    process_convergence = [
        f"{bp.name} ({bp.canonical_id}) is associated with gene(s): {', '.join(sorted(bp_genes[bp.id]))}"
        for bp in processes
        if len(bp_genes[bp.id]) >= 1
    ]

    return BiologicalAnalysisResponse(
        compound=compound_summary,
        target_protein_count=len(proteins),
        associated_gene_count=len(genes),
        connected_pathways=connected_pathways,
        connected_processes=connected_processes,
        pathway_convergence=pathway_convergence,
        process_convergence=process_convergence,
    )
