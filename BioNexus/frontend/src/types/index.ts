export interface HealthStatus {
  status: string;
  service: string;
  database?: string;
  detail?: string;
}

export interface CompoundSummary {
  id?: string;
  name: string;
  canonical_id?: string;
  pubchem_cid?: number;
  formula?: string;
  smiles?: string;
  molecular_weight?: number;
  source?: string;
}

export interface CompoundSearchResponse {
  query: string;
  total_matches: number;
  items: CompoundSummary[];
  message: string;
  metadata?: Record<string, any>;
}

export interface GraphEvidence {
  id: number;
  source_database: string;
  source_record_id?: string;
  evidence_type?: string;
  confidence?: number;
  source_url?: string;
  retrieved_at?: string;
}

export interface GraphNode {
  id: string;
  db_id: number;
  canonical_id: string;
  name: string;
  entity_type: "compound" | "protein" | "gene" | "pathway" | "biological_process";
  metadata?: Record<string, any>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relationship_type: string;
  relationship_id: number;
  is_documented: boolean;
  evidence?: GraphEvidence[];
}

export interface GraphStatistics {
  node_count: number;
  edge_count: number;
  node_types: Record<string, number>;
  relationship_types: Record<string, number>;
  connected_components: number;
}

export interface CompoundGraphResponse {
  compound?: CompoundSummary;
  nodes: GraphNode[];
  edges: GraphEdge[];
  statistics: GraphStatistics;
}

export interface CentralityScore {
  node_id: string;
  db_id: number;
  name: string;
  canonical_id: string;
  entity_type: string;
  degree_centrality: number;
  betweenness_centrality: number;
  connectivity_label: string;
}

export interface GraphPath {
  path_type: string;
  nodes: string[];
  node_names: string[];
  length: number;
  is_documented_direct: boolean;
}

export interface ConvergencePoint {
  node_id: string;
  db_id: number;
  name: string;
  canonical_id: string;
  entity_type: string;
  in_degree: number;
  incoming_sources: string[];
}

export interface GraphAnalysisResponse {
  compound: CompoundSummary;
  total_nodes: number;
  total_edges: number;
  central_nodes: CentralityScore[];
  convergence_points: ConvergencePoint[];
  paths: GraphPath[];
  relationship_distribution: Record<string, number>;
  connected_components: number;
  summary: string;
}

export interface BiologicalPathwaySummary {
  pathway_id: number;
  canonical_id: string;
  name: string;
  mediating_genes: string[];
  mediating_proteins: string[];
}

export interface BiologicalProcessDetail {
  process_id: number;
  canonical_id: string;
  name: string;
  mediating_genes: string[];
}

export interface BiologicalAnalysisResponse {
  compound: CompoundSummary;
  target_protein_count: number;
  associated_gene_count: number;
  connected_pathways: BiologicalPathwaySummary[];
  connected_processes: BiologicalProcessDetail[];
  pathway_convergence: string[];
  process_convergence: string[];
  analysis_type: string;
  scientific_note: string;
}

export interface EvidenceInsight {
  finding: string;
  relationship_type: "DOCUMENTED" | "GRAPH_DERIVED";
  source_entity: string;
  target_entity: string;
  supporting_path: string[];
  evidence_records: GraphEvidence[];
}

export interface CompoundEvidenceResponse {
  compound: CompoundSummary;
  total_documented_relationships: number;
  total_graph_derived_relationships: number;
  documented_evidence: EvidenceInsight[];
  graph_derived_insights: EvidenceInsight[];
}

export interface GeminiExplanationResponse {
  compound_name: string;
  canonical_id: string;
  explanation: string;
  documented_findings: string[];
  graph_derived_findings: string[];
  evidence_citations: string[];
  scientific_limitations: string;
  model_used: string;
  generated_at?: string;
}
