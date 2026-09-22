"""Gemini LLM grounded biological explanation service.

Translates verified knowledge graph findings, pathway connections, and literature evidence
into concise, evidence-grounded scientific explanations.
Strictly prohibits hallucinating biological entities, citations, or statistical claims.
"""

import json
import logging
from typing import Any, Dict, List, Optional
import httpx
from ...core.config import settings
from ...schemas.analysis import GeminiExplanationResponse

logger = logging.getLogger("bionexus.llm.gemini")

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"


def _build_structured_prompt(context: Dict[str, Any], focus_area: Optional[str] = None) -> str:
    """Format structured biological context for strictly grounded Gemini inference."""
    compound = context.get("compound", {})
    proteins = context.get("target_proteins", [])
    genes = context.get("associated_genes", [])
    pathways = context.get("pathways", [])
    processes = context.get("biological_processes", [])
    evidence = context.get("evidence", [])
    graph_analysis = context.get("graph_analysis", {})

    protein_names = [f"{p.get('name')} (UniProt: {p.get('canonical_id')})" for p in proteins]
    gene_names = [f"{g.get('name')} (Symbol: {g.get('canonical_id')})" for g in genes]
    pathway_names = [f"{pw.get('name')} (Reactome: {pw.get('canonical_id')})" for pw in pathways]
    process_names = [f"{bp.get('name')} (GO: {bp.get('canonical_id')})" for bp in processes]
    citations = [
        f"{e.get('source_database')} PMID:{e.get('source_record_id')} ({e.get('evidence_type')})"
        for e in evidence
        if e.get("source_record_id")
    ]

    prompt = f"""You are BioNexus AI, an evidence-grounded biological discovery assistant.

CRITICAL SCIENTIFIC INSTRUCTIONS:
1. You must use ONLY the supplied biological findings and evidence below.
2. DO NOT invent or hallucinate biological relationships, protein targets, genes, pathways, or citations.
3. Clearly distinguish DOCUMENTED relationships (directly supported by literature citations/PMIDs) from GRAPH-DERIVED paths (multi-hop graph connections through encoding genes).
4. If evidence is limited or absent for any connection, explicitly state so.
5. Provide a clear, professional synthesis formatted in clean Markdown.

STRUCTURED BIOLOGICAL FINDINGS FOR: {compound.get('name')} (Canonical ID: {compound.get('canonical_id')})
- PubChem CID: {compound.get('pubchem_cid')}
- Molecular Weight: {compound.get('molecular_weight')} g/mol
- SMILES: {compound.get('smiles')}

DOCUMENTED TARGET PROTEINS (UniProt):
{chr(10).join(f'- {p}' for p in protein_names) if protein_names else '- None documented'}

ENCODING GENES (HGNC / NCBI):
{chr(10).join(f'- {g}' for g in gene_names) if gene_names else '- None documented'}

GRAPH-CONNECTED PATHWAYS (Reactome):
{chr(10).join(f'- {pw}' for pw in pathway_names) if pathway_names else '- None documented'}

GRAPH-CONNECTED BIOLOGICAL PROCESSES (Gene Ontology):
{chr(10).join(f'- {bp}' for bp in process_names) if process_names else '- None documented'}

LITERATURE EVIDENCE & CITATIONS:
{chr(10).join(f'- {c}' for c in citations) if citations else '- No direct PubMed citations available'}

GRAPH CENTRALITY & CONVERGENCE:
- Total Graph Nodes: {graph_analysis.get('total_nodes', len(proteins) + len(genes) + len(pathways) + len(processes) + 1)}
- Total Graph Edges: {graph_analysis.get('total_edges', len(proteins) + len(genes) + len(pathways) + len(processes))}
{f"Focus Area Requested: {focus_area}" if focus_area else ""}

Please provide:
1. Executive Summary: What is this natural compound and its primary biological mechanism?
2. Documented Target Interactions: Verified molecular targets and literature evidence.
3. Graph-Derived Pathway & Functional Cascades: Downstream pathways and cellular processes reached via encoding genes.
4. Scientific Limitations: Clear statement on evidence boundaries and graph traversal caveats.
"""
    return prompt


def _generate_fallback_explanation(
    context: Dict[str, Any],
    reason: str = "GEMINI_API_KEY_UNCONFIGURED",
) -> GeminiExplanationResponse:
    """Generate a high-quality deterministic structured explanation when LLM API key is not set."""
    compound = context.get("compound", {})
    compound_name = compound.get("name", "Unknown Compound")
    canonical_id = compound.get("canonical_id", "")
    proteins = context.get("target_proteins", [])
    genes = context.get("associated_genes", [])
    pathways = context.get("pathways", [])
    processes = context.get("biological_processes", [])
    evidence = context.get("evidence", [])

    protein_list = [p.get("name") for p in proteins if p.get("name")]
    gene_list = [g.get("canonical_id") for g in genes if g.get("canonical_id")]
    pathway_list = [pw.get("name") for pw in pathways if pw.get("name")]
    process_list = [bp.get("name") for bp in processes if bp.get("name")]
    citations = [
        f"{e.get('source_database')} PMID:{e.get('source_record_id')}"
        for e in evidence
        if e.get("source_record_id")
    ]

    doc_findings = [
        f"Directly targets {p.get('name')} (UniProt: {p.get('canonical_id')})"
        for p in proteins
    ]

    derived_findings = [
        f"Encapsulates cascade to pathway '{pw}' via gene(s) {', '.join(gene_list)}"
        for pw in pathway_list
    ] + [
        f"Regulates biological process '{bp}'"
        for bp in process_list
    ]

    explanation_md = f"""### Biological Knowledge Graph Synthesis: {compound_name}

**Overview**:
`{compound_name}` (StreptomeDB ID: `{canonical_id}`) is a natural compound with verified biological target interactions in the BioNexus knowledge graph.

#### 1. Documented Molecular Targets
- **Target Protein(s)**: {', '.join(protein_list) if protein_list else 'No target proteins documented'}
- **Literature Grounding**: {', '.join(citations) if citations else 'No direct PubMed PMIDs recorded'}

#### 2. Downstream Graph-Derived Cascades
Through gene encoding linkages ({', '.join(gene_list) if gene_list else 'N/A'}), this compound's mechanism connects to:
- **Signaling & Metabolic Pathways**: {', '.join(pathway_list) if pathway_list else 'None'}
- **Biological Processes**: {', '.join(process_list) if process_list else 'None'}

> [!NOTE]
> *Status Note*: {('Gemini API key is unconfigured in backend environment. Serving structured knowledge graph synthesis.' if reason == 'GEMINI_API_KEY_UNCONFIGURED' else f'AI service notice: {reason}')}
"""

    return GeminiExplanationResponse(
        compound_name=compound_name,
        canonical_id=canonical_id,
        explanation=explanation_md,
        documented_findings=doc_findings,
        graph_derived_findings=derived_findings,
        evidence_citations=citations,
        scientific_limitations=(
            "Findings strictly reflect curated database relationships in UniProt, Reactome, and Gene Ontology. "
            "Graph-derived paths represent functional connectivity and do not imply direct enzymatic inhibition."
        ),
        model_used="bionexus-grounded-rule-engine" if reason == "GEMINI_API_KEY_UNCONFIGURED" else "gemini-1.5-flash-fallback",
    )


async def generate_compound_explanation(
    context: Dict[str, Any],
    focus_area: Optional[str] = None,
) -> GeminiExplanationResponse:
    """Generate evidence-grounded natural language explanation using Gemini API."""
    api_key = settings.GEMINI_API_KEY.strip() if settings.GEMINI_API_KEY else ""

    if not api_key:
        logger.info("GEMINI_API_KEY not configured. Returning deterministic grounded synthesis.")
        return _generate_fallback_explanation(context, reason="GEMINI_API_KEY_UNCONFIGURED")

    prompt = _build_structured_prompt(context, focus_area=focus_area)
    compound = context.get("compound", {})
    compound_name = compound.get("name", "Unknown Compound")
    canonical_id = compound.get("canonical_id", "")
    proteins = context.get("target_proteins", [])
    pathways = context.get("pathways", [])
    processes = context.get("biological_processes", [])
    evidence = context.get("evidence", [])

    doc_findings = [f"Directly targets {p.get('name')} ({p.get('canonical_id')})" for p in proteins]
    derived_findings = [f"Pathway: {pw.get('name')}" for pw in pathways] + [f"Process: {bp.get('name')}" for bp in processes]
    citations = [f"{e.get('source_database')} PMID:{e.get('source_record_id')}" for e in evidence if e.get("source_record_id")]

    url = f"{GEMINI_API_URL}?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,  # Low temperature for strict scientific grounding
            "maxOutputTokens": 1024,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        text_resp = parts[0].get("text", "")
                        return GeminiExplanationResponse(
                            compound_name=compound_name,
                            canonical_id=canonical_id,
                            explanation=text_resp,
                            documented_findings=doc_findings,
                            graph_derived_findings=derived_findings,
                            evidence_citations=citations,
                            scientific_limitations="Generated by Gemini 1.5 Flash strictly constrained to BioNexus knowledge graph findings.",
                            model_used="gemini-1.5-flash",
                        )
            logger.warning(f"Gemini API returned status {resp.status_code}: {resp.text[:200]}")
            return _generate_fallback_explanation(context, reason=f"Gemini API status {resp.status_code}")
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        return _generate_fallback_explanation(context, reason=f"Gemini API request error: {type(e).__name__}")
