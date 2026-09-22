"""FastAPI route handlers for natural compounds and integrated biological entities."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from ...db.models import BiologicalProcess, Compound, Evidence, Gene, Pathway, Protein, Relationship
from ...db.session import get_db
from ...schemas.analysis import (
    BiologicalAnalysisResponse,
    CompoundEvidenceResponse,
    EvidenceInsight,
    GeminiExplanationRequest,
    GeminiExplanationResponse,
    GraphAnalysisResponse,
)
from ...schemas.compound import (
    BiologicalProcessSummary,
    CompoundDetailResponse,
    CompoundSearchResponse,
    CompoundSummary,
    EvidenceSummary,
    GeneSummary,
    PathwaySummary,
    ProteinSummary,
)
from ...services.analysis import analyze_compound_biology, analyze_compound_graph
from ...services.graph import CompoundGraphResponse, get_compound_graph_by_id
from ...services.llm import generate_compound_explanation

router = APIRouter(prefix="/compounds", tags=["Compounds"])


def _find_compound(db: Session, compound_id: str) -> Optional[Compound]:
    """Helper to find compound by primary key integer id or canonical_id string."""
    if compound_id.isdigit():
        compound = db.execute(
            select(Compound).where(Compound.id == int(compound_id))
        ).scalar_one_or_none()
        if compound:
            return compound

    return db.execute(
        select(Compound).where(Compound.canonical_id == compound_id)
    ).scalar_one_or_none()


@router.get("/search", response_model=CompoundSearchResponse)
async def search_compounds(
    q: str = Query(
        ...,
        min_length=1,
        description="Search query string for natural compound, metabolite, or chemical synonym",
        examples=["curcumin", "resveratrol", "capreomycin", "doxorubicin"],
    ),
    db: Optional[Session] = Depends(get_db),
) -> CompoundSearchResponse:
    """Search for biological natural compounds in TiDB database.

    Queries the `compounds` table by name or canonical_id.
    Returns clean empty structure if database is empty or unpopulated.
    """
    cleaned_query = q.strip()
    matched_items = []

    if db is not None:
        try:
            search_pattern = f"%{cleaned_query}%"
            stmt = (
                select(Compound)
                .where(
                    or_(
                        Compound.name.ilike(search_pattern),
                        Compound.canonical_id.ilike(search_pattern),
                    )
                )
                .order_by(Compound.name.asc())
                .limit(50)
            )
            results = db.execute(stmt).scalars().all()

            for compound in results:
                matched_items.append(
                    CompoundSummary(
                        id=str(compound.id),
                        name=compound.name,
                        canonical_id=compound.canonical_id,
                        pubchem_cid=compound.pubchem_cid,
                        formula=None,
                        smiles=compound.smiles,
                        molecular_weight=compound.molecular_weight,
                        source=f"StreptomeDB (canonical_id: {compound.canonical_id})",
                    )
                )
        except Exception:
            matched_items = []

    total = len(matched_items)
    message = (
        f"Found {total} matching compound(s) in TiDB database."
        if total > 0
        else f"Query received for '{cleaned_query}'. 0 records found in database."
    )

    return CompoundSearchResponse(
        query=cleaned_query,
        total_matches=total,
        items=matched_items,
        message=message,
        metadata={
            "database_queried": db is not None,
            "total_matches": total,
        },
    )


@router.get("/{compound_id}", response_model=CompoundDetailResponse)
async def get_compound_detail(
    compound_id: str,
    db: Optional[Session] = Depends(get_db),
) -> CompoundDetailResponse:
    """Get complete biological context for a natural compound.

    Returns the compound and all linked:
    - Target proteins (UniProt)
    - Encoding genes (HGNC / NCBI)
    - Biological pathways (Reactome)
    - Biological processes (Gene Ontology)
    - Grounding evidence (PubMed citations)
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is not available.",
        )

    compound = _find_compound(db, compound_id)
    if not compound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compound '{compound_id}' not found.",
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
    rel_ids = [rel.id for rel in protein_rels]

    proteins = []
    if protein_ids:
        proteins = db.execute(
            select(Protein).where(Protein.id.in_(protein_ids))
        ).scalars().all()

    protein_summaries = [
        ProteinSummary(
            id=p.id,
            name=p.name,
            canonical_id=p.canonical_id,
            relationship_type="targets",
            created_at=p.created_at,
        )
        for p in proteins
    ]

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

    gene_summaries = [
        GeneSummary(
            id=g.id,
            name=g.name,
            canonical_id=g.canonical_id,
            created_at=g.created_at,
        )
        for g in genes
    ]

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

    pathway_summaries = [
        PathwaySummary(
            id=pw.id,
            name=pw.name,
            canonical_id=pw.canonical_id,
            created_at=pw.created_at,
        )
        for pw in pathways
    ]

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

    process_summaries = [
        BiologicalProcessSummary(
            id=bp.id,
            name=bp.name,
            canonical_id=bp.canonical_id,
            created_at=bp.created_at,
        )
        for bp in processes
    ]

    # 5. Evidence
    evidence_records = []
    if rel_ids:
        evidence_records = db.execute(
            select(Evidence).where(Evidence.relationship_id.in_(rel_ids))
        ).scalars().all()

    evidence_summaries = [
        EvidenceSummary(
            id=ev.id,
            relationship_id=ev.relationship_id,
            source_database=ev.source_database,
            source_record_id=ev.source_record_id,
            evidence_type=ev.evidence_type,
            confidence=ev.confidence,
            source_url=ev.source_url,
            retrieved_at=ev.retrieved_at,
        )
        for ev in evidence_records
    ]

    return CompoundDetailResponse(
        compound=CompoundSummary(
            id=str(compound.id),
            name=compound.name,
            canonical_id=compound.canonical_id,
            pubchem_cid=compound.pubchem_cid,
            smiles=compound.smiles,
            molecular_weight=compound.molecular_weight,
            source=f"StreptomeDB (canonical_id: {compound.canonical_id})",
        ),
        target_proteins=protein_summaries,
        associated_genes=gene_summaries,
        pathways=pathway_summaries,
        biological_processes=process_summaries,
        evidence=evidence_summaries,
    )


@router.get("/{compound_id}/proteins", response_model=List[ProteinSummary])
async def get_compound_proteins(
    compound_id: str,
    db: Optional[Session] = Depends(get_db),
) -> List[ProteinSummary]:
    """Retrieve target proteins for a natural compound."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is not available.",
        )

    compound = _find_compound(db, compound_id)
    if not compound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compound '{compound_id}' not found.",
        )

    stmt = (
        select(Protein)
        .join(
            Relationship,
            (Relationship.target_id == Protein.id)
            & (Relationship.target_type == "protein")
            & (Relationship.relationship_type == "targets")
            & (Relationship.source_type == "compound")
            & (Relationship.source_id == compound.id),
        )
    )
    proteins = db.execute(stmt).scalars().all()

    return [
        ProteinSummary(
            id=p.id,
            name=p.name,
            canonical_id=p.canonical_id,
            relationship_type="targets",
            created_at=p.created_at,
        )
        for p in proteins
    ]


@router.get("/{compound_id}/genes", response_model=List[GeneSummary])
async def get_compound_genes(
    compound_id: str,
    db: Optional[Session] = Depends(get_db),
) -> List[GeneSummary]:
    """Retrieve encoding genes associated with compound target proteins."""
    detail = await get_compound_detail(compound_id, db)
    return detail.associated_genes


@router.get("/{compound_id}/pathways", response_model=List[PathwaySummary])
async def get_compound_pathways(
    compound_id: str,
    db: Optional[Session] = Depends(get_db),
) -> List[PathwaySummary]:
    """Retrieve biological pathways connected to the compound via associated genes."""
    detail = await get_compound_detail(compound_id, db)
    return detail.pathways


@router.get("/{compound_id}/processes", response_model=List[BiologicalProcessSummary])
async def get_compound_processes(
    compound_id: str,
    db: Optional[Session] = Depends(get_db),
) -> List[BiologicalProcessSummary]:
    """Retrieve biological processes (Gene Ontology) connected to the compound."""
    detail = await get_compound_detail(compound_id, db)
    return detail.biological_processes


@router.get("/{compound_id}/evidence", response_model=List[EvidenceSummary])
async def get_compound_evidence(
    compound_id: str,
    db: Optional[Session] = Depends(get_db),
) -> List[EvidenceSummary]:
    """Retrieve literature evidence records grounding the compound-target interactions."""
    detail = await get_compound_detail(compound_id, db)
    return detail.evidence


@router.get("/{compound_id}/graph", response_model=CompoundGraphResponse)
async def get_compound_graph(
    compound_id: str,
    db: Optional[Session] = Depends(get_db),
) -> CompoundGraphResponse:
    """Retrieve the complete Cytoscape.js compatible biological knowledge graph for a compound.

    Returns:
    - `nodes`: Compound, target proteins, encoding genes, pathways, and biological processes
    - `edges`: Documented relationships with attached literature evidence
    - `statistics`: Node/edge type breakdowns and connected components
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is not available.",
        )

    graph_data = get_compound_graph_by_id(db, compound_id)
    if not graph_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compound '{compound_id}' not found.",
        )

    return graph_data


@router.get("/{compound_id}/analysis", response_model=GraphAnalysisResponse)
async def get_compound_graph_analysis(
    compound_id: str,
    db: Optional[Session] = Depends(get_db),
) -> GraphAnalysisResponse:
    """Step 6: Perform computational graph analysis (centrality, paths, convergence points)."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is not available.",
        )

    compound = _find_compound(db, compound_id)
    if not compound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compound '{compound_id}' not found.",
        )

    return analyze_compound_graph(db, compound)


@router.get("/{compound_id}/biological-analysis", response_model=BiologicalAnalysisResponse)
async def get_compound_biological_analysis(
    compound_id: str,
    db: Optional[Session] = Depends(get_db),
) -> BiologicalAnalysisResponse:
    """Step 7: Perform biological and pathway analysis (Reactome pathways, GO processes, convergence)."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is not available.",
        )

    compound = _find_compound(db, compound_id)
    if not compound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compound '{compound_id}' not found.",
        )

    return analyze_compound_biology(db, compound)


@router.get("/{compound_id}/provenance", response_model=CompoundEvidenceResponse)
async def get_compound_provenance(
    compound_id: str,
    db: Optional[Session] = Depends(get_db),
) -> CompoundEvidenceResponse:
    """Step 8: Structured evidence provenance distinguishing DOCUMENTED from GRAPH_DERIVED findings."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is not available.",
        )

    detail = await get_compound_detail(compound_id, db)
    graph_analysis = analyze_compound_graph(db, _find_compound(db, compound_id))

    documented: List[EvidenceInsight] = []
    # Direct compound -> target protein evidence
    for prot in detail.target_proteins:
        ev_records = [e for e in detail.evidence if e.relationship_id]
        documented.append(
            EvidenceInsight(
                finding=f"{detail.compound.name} directly targets protein {prot.name} ({prot.canonical_id})",
                relationship_type="DOCUMENTED",
                source_entity=detail.compound.name,
                target_entity=prot.name,
                supporting_path=[detail.compound.name, prot.name],
                evidence_records=ev_records,
            )
        )

    derived: List[EvidenceInsight] = []
    # Graph-derived pathway and process connections
    for pw in detail.pathways:
        derived.append(
            EvidenceInsight(
                finding=f"{detail.compound.name} connects downstream to pathway '{pw.name}' via encoding genes",
                relationship_type="GRAPH_DERIVED",
                source_entity=detail.compound.name,
                target_entity=pw.name,
                supporting_path=[detail.compound.name, "Target Protein", "Encoding Gene", pw.name],
                evidence_records=[],
            )
        )

    for bp in detail.biological_processes:
        derived.append(
            EvidenceInsight(
                finding=f"{detail.compound.name} is associated with biological process '{bp.name}'",
                relationship_type="GRAPH_DERIVED",
                source_entity=detail.compound.name,
                target_entity=bp.name,
                supporting_path=[detail.compound.name, "Target Protein", "Encoding Gene", bp.name],
                evidence_records=[],
            )
        )

    return CompoundEvidenceResponse(
        compound=detail.compound,
        total_documented_relationships=len(documented),
        total_graph_derived_relationships=len(derived),
        documented_evidence=documented,
        graph_derived_insights=derived,
    )


@router.post("/{compound_id}/explanation", response_model=GeminiExplanationResponse)
async def get_compound_explanation(
    compound_id: str,
    request: Optional[GeminiExplanationRequest] = None,
    db: Optional[Session] = Depends(get_db),
) -> GeminiExplanationResponse:
    """Step 9: Evidence-grounded natural language explanation generated by Gemini."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is not available.",
        )

    compound = _find_compound(db, compound_id)
    if not compound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compound '{compound_id}' not found.",
        )

    detail = await get_compound_detail(compound_id, db)
    graph_analysis = analyze_compound_graph(db, compound)
    bio_analysis = analyze_compound_biology(db, compound)

    context = {
        "compound": detail.compound.model_dump(),
        "target_proteins": [p.model_dump() for p in detail.target_proteins],
        "associated_genes": [g.model_dump() for g in detail.associated_genes],
        "pathways": [pw.model_dump() for pw in detail.pathways],
        "biological_processes": [bp.model_dump() for bp in detail.biological_processes],
        "evidence": [ev.model_dump() for ev in detail.evidence],
        "graph_analysis": graph_analysis.model_dump(),
        "biological_analysis": bio_analysis.model_dump(),
    }

    focus = request.focus_area if request else None
    return await generate_compound_explanation(context, focus_area=focus)
