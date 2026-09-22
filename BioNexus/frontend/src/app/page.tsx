"use client";

import React, { useEffect, useState } from "react";
import CytoscapeGraph from "@/components/CytoscapeGraph";
import {
  BiologicalAnalysisResponse,
  CompoundEvidenceResponse,
  CompoundGraphResponse,
  CompoundSearchResponse,
  CompoundSummary,
  GeminiExplanationResponse,
  GraphAnalysisResponse,
  GraphEdge,
  GraphNode,
  HealthStatus,
} from "@/types";
import {
  Activity,
  AlertCircle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Database,
  Dna,
  ExternalLink,
  GitFork,
  HelpCircle,
  Layers,
  Network,
  Search,
  Sparkles,
  Zap,
} from "lucide-react";

const API_BASE = "/api";

const QUICK_COMPOUNDS = [
  "Doxorubicin",
  "Rapamycin",
  "Capreomycin",
  "Tacrolimus",
  "Mitomycin C",
  "Erythromycin",
  "Novobiocin",
];

export default function BioNexusDashboard() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [searchQuery, setSearchQuery] = useState("Doxorubicin");
  const [searchResults, setSearchResults] = useState<CompoundSummary[]>([]);
  const [selectedCompound, setSelectedCompound] = useState<CompoundSummary | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  // Active Tab
  const [activeTab, setActiveTab] = useState<"graph" | "analysis" | "biology" | "evidence" | "gemini">("graph");

  // Detailed Data States
  const [graphData, setGraphData] = useState<CompoundGraphResponse | null>(null);
  const [graphAnalysis, setGraphAnalysis] = useState<GraphAnalysisResponse | null>(null);
  const [bioAnalysis, setBioAnalysis] = useState<BiologicalAnalysisResponse | null>(null);
  const [provenanceData, setProvenanceData] = useState<CompoundEvidenceResponse | null>(null);

  // Gemini State
  const [explanation, setExplanation] = useState<GeminiExplanationResponse | null>(null);
  const [isGeneratingExplanation, setIsGeneratingExplanation] = useState(false);
  const [explanationError, setExplanationError] = useState<string | null>(null);

  // Inspector State
  const [inspectedNode, setInspectedNode] = useState<GraphNode | null>(null);
  const [inspectedEdge, setInspectedEdge] = useState<GraphEdge | null>(null);

  // Loading States
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);

  // Check Backend Health on Mount + periodic refresh
  useEffect(() => {
    const fetchHealth = () => {
      fetch(`${API_BASE}/health`)
        .then((res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return res.json();
        })
        .then((data) => setHealth(data))
        .catch(() => setHealth({ status: "error", service: "BioNexus API", database: "disconnected" }));
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 5000);

    // Initial search for default compound
    handleSearch("Doxorubicin");

    return () => clearInterval(interval);
  }, []);

  const handleSearch = async (queryToSearch?: string) => {
    const q = queryToSearch !== undefined ? queryToSearch : searchQuery;
    if (!q.trim()) return;

    setIsSearching(true);
    try {
      const res = await fetch(`${API_BASE}/compounds/search?q=${encodeURIComponent(q)}`);
      const data: CompoundSearchResponse = await res.json();
      const items = data.items || [];
      setSearchResults(items);

      if (items.length > 0) {
        // Find exact name match or canonical ID match first, else pick first item
        const exactMatch = items.find(
          (item) =>
            item.name.toLowerCase() === q.trim().toLowerCase() ||
            item.canonical_id?.toLowerCase() === q.trim().toLowerCase()
        ) || items[0];
        selectCompound(exactMatch);
      } else {
        setSelectedCompound(null);
        setGraphData(null);
        setGraphAnalysis(null);
        setBioAnalysis(null);
        setProvenanceData(null);
      }
    } catch (err) {
      console.error("Search failed:", err);
    } finally {
      setIsSearching(false);
    }
  };

  const selectCompound = async (compound: CompoundSummary) => {
    setSelectedCompound(compound);
    setInspectedNode(null);
    setInspectedEdge(null);
    setExplanation(null);
    setExplanationError(null);
    setIsLoadingDetails(true);

    const compId = compound.id || compound.canonical_id || "";

    try {
      // Fetch Graph, Analysis, Biological Analysis, Provenance in parallel with resilience
      const [gRes, aRes, bRes, pRes] = await Promise.allSettled([
        fetch(`${API_BASE}/compounds/${compId}/graph`).then((r) => (r.ok ? r.json() : null)),
        fetch(`${API_BASE}/compounds/${compId}/analysis`).then((r) => (r.ok ? r.json() : null)),
        fetch(`${API_BASE}/compounds/${compId}/biological-analysis`).then((r) => (r.ok ? r.json() : null)),
        fetch(`${API_BASE}/compounds/${compId}/provenance`).then((r) => (r.ok ? r.json() : null)),
      ]);

      setGraphData(gRes.status === "fulfilled" && gRes.value ? gRes.value : null);
      setGraphAnalysis(aRes.status === "fulfilled" && aRes.value ? aRes.value : null);
      setBioAnalysis(bRes.status === "fulfilled" && bRes.value ? bRes.value : null);
      setProvenanceData(pRes.status === "fulfilled" && pRes.value ? pRes.value : null);
    } catch (err) {
      console.error("Failed to load compound biological data:", err);
    } finally {
      setIsLoadingDetails(false);
    }
  };

  const handleGenerateExplanation = async () => {
    if (!selectedCompound) return;
    const compId = selectedCompound.id || selectedCompound.canonical_id || "";

    setIsGeneratingExplanation(true);
    setExplanationError(null);

    try {
      const res = await fetch(`${API_BASE}/compounds/${compId}/explanation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`);
      }

      const data: GeminiExplanationResponse = await res.json();
      setExplanation(data);
    } catch (err: any) {
      setExplanationError(err.message || "Failed to generate explanation");
    } finally {
      setIsGeneratingExplanation(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-emerald-500 selection:text-white">
      {/* Top Navbar */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 via-teal-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <Dna className="w-6 h-6 text-slate-950" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 bg-clip-text text-transparent">
                  BioNexus
                </span>
                <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Knowledge Graph v1.0
                </span>
              </div>
              <p className="text-xs text-slate-400">Evidence-Grounded Natural Compound Discovery</p>
            </div>
          </div>

          {/* Database / Backend Status Indicator */}
          <div className="flex items-center gap-3 text-xs">
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60">
              <Database className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-slate-300">TiDB Cloud:</span>
              <span
                className={`font-medium ${
                  health?.database === "connected" ? "text-emerald-400" : "text-amber-400"
                }`}
              >
                {health?.database || "checking..."}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Search & Quick Select Bar */}
        <section className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 sm:p-5 shadow-xl backdrop-blur-sm">
          <div className="flex flex-col sm:flex-row gap-3 items-stretch">
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder="Search StreptomeDB natural compounds (e.g., Doxorubicin, Rapamycin, Capreomycin)..."
                className="w-full bg-slate-950 border border-slate-700 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition"
              />
            </div>
            <button
              onClick={() => handleSearch()}
              disabled={isSearching}
              className="px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-medium rounded-xl text-sm transition shadow-lg shadow-emerald-600/20 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isSearching ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <Search className="w-4 h-4" />
              )}
              Search
            </button>
          </div>

          {/* Quick Selection Pills */}
          <div className="flex flex-wrap items-center gap-2 mt-3 text-xs">
            <span className="text-slate-400 font-medium">Quick Select:</span>
            {QUICK_COMPOUNDS.map((cName) => (
              <button
                key={cName}
                onClick={() => {
                  setSearchQuery(cName);
                  handleSearch(cName);
                }}
                className={`px-2.5 py-1 rounded-lg border transition ${
                  selectedCompound?.name === cName
                    ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40 font-medium"
                    : "bg-slate-800/60 text-slate-300 border-slate-700 hover:bg-slate-800 hover:text-white"
                }`}
              >
                {cName}
              </button>
            ))}
          </div>

          {/* Search Result Matches (if multiple) */}
          {searchResults.length > 1 && (
            <div className="flex flex-wrap items-center gap-2 mt-2 pt-2 border-t border-slate-800/60 text-xs">
              <span className="text-slate-400 font-medium">Matches ({searchResults.length}):</span>
              {searchResults.slice(0, 8).map((item) => (
                <button
                  key={item.id}
                  onClick={() => selectCompound(item)}
                  className={`px-2 py-0.5 rounded-md border text-[11px] transition ${
                    selectedCompound?.id === item.id
                      ? "bg-teal-500/20 text-teal-300 border-teal-500/40 font-semibold"
                      : "bg-slate-950/60 text-slate-400 border-slate-800 hover:text-slate-200"
                  }`}
                >
                  {item.name} ({item.canonical_id})
                </button>
              ))}
            </div>
          )}
        </section>



        {/* Dashboard Tabs */}
        <div className="border-b border-slate-800 flex items-center gap-2 overflow-x-auto pb-px">
          <button
            onClick={() => setActiveTab("graph")}
            className={`px-4 py-2.5 text-sm font-medium rounded-t-xl border-b-2 flex items-center gap-2 transition whitespace-nowrap ${
              activeTab === "graph"
                ? "border-emerald-500 text-emerald-400 bg-slate-900/60"
                : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700"
            }`}
          >
            <Network className="w-4 h-4" />
            Knowledge Graph (Cytoscape)
          </button>
          <button
            onClick={() => setActiveTab("analysis")}
            className={`px-4 py-2.5 text-sm font-medium rounded-t-xl border-b-2 flex items-center gap-2 transition whitespace-nowrap ${
              activeTab === "analysis"
                ? "border-emerald-500 text-emerald-400 bg-slate-900/60"
                : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700"
            }`}
          >
            <Activity className="w-4 h-4" />
            Graph Analysis
          </button>
          <button
            onClick={() => setActiveTab("biology")}
            className={`px-4 py-2.5 text-sm font-medium rounded-t-xl border-b-2 flex items-center gap-2 transition whitespace-nowrap ${
              activeTab === "biology"
                ? "border-emerald-500 text-emerald-400 bg-slate-900/60"
                : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700"
            }`}
          >
            <Layers className="w-4 h-4" />
            Pathway & Biological Analysis
          </button>
          <button
            onClick={() => setActiveTab("evidence")}
            className={`px-4 py-2.5 text-sm font-medium rounded-t-xl border-b-2 flex items-center gap-2 transition whitespace-nowrap ${
              activeTab === "evidence"
                ? "border-emerald-500 text-emerald-400 bg-slate-900/60"
                : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700"
            }`}
          >
            <BookOpen className="w-4 h-4" />
            Evidence & Provenance
          </button>
          <button
            onClick={() => setActiveTab("gemini")}
            className={`px-4 py-2.5 text-sm font-medium rounded-t-xl border-b-2 flex items-center gap-2 transition whitespace-nowrap ${
              activeTab === "gemini"
                ? "border-emerald-500 text-emerald-400 bg-slate-900/60"
                : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700"
            }`}
          >
            <Sparkles className="w-4 h-4 text-amber-400" />
            Gemini AI Explanation
          </button>
        </div>

        {/* Tab 1: Interactive Knowledge Graph */}
        {activeTab === "graph" && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Cytoscape Canvas */}
            <div className="lg:col-span-3">
              {isLoadingDetails ? (
                <div className="w-full h-[520px] rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-center">
                  <div className="flex flex-col items-center gap-3">
                    <div className="w-8 h-8 border-3 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
                    <span className="text-sm text-slate-400">Loading Biological Knowledge Graph...</span>
                  </div>
                </div>
              ) : graphData && graphData.nodes.length > 0 ? (
                <CytoscapeGraph
                  graphData={graphData}
                  onNodeSelect={(n) => {
                    setInspectedNode(n);
                    setInspectedEdge(null);
                  }}
                  onEdgeSelect={(e) => {
                    setInspectedEdge(e);
                    setInspectedNode(null);
                  }}
                />
              ) : (
                <div className="w-full h-[520px] rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-center text-slate-400 text-sm">
                  No graph connections found for this compound.
                </div>
              )}
            </div>

            {/* Sidebar Inspector */}
            <div className="lg:col-span-1 bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex flex-col h-[520px] overflow-y-auto">
              <h3 className="font-semibold text-sm text-slate-200 mb-3 flex items-center gap-2">
                <Search className="w-4 h-4 text-emerald-400" />
                Entity & Edge Inspector
              </h3>

              {inspectedNode ? (
                <div className="space-y-3 text-xs">
                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                    <span className="text-[10px] uppercase font-bold text-slate-400">Entity Type</span>
                    <p className="font-semibold text-emerald-400 capitalize text-sm">{inspectedNode.entity_type}</p>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">Name:</span>
                    <p className="font-semibold text-slate-200">{inspectedNode.name}</p>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">Canonical ID:</span>
                    <p className="font-mono text-slate-300 bg-slate-950 px-2 py-1 rounded border border-slate-800 mt-0.5">
                      {inspectedNode.canonical_id}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">Database ID:</span>
                    <p className="text-slate-300 font-mono">{inspectedNode.db_id}</p>
                  </div>
                </div>
              ) : inspectedEdge ? (
                <div className="space-y-3 text-xs">
                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                    <span className="text-[10px] uppercase font-bold text-slate-400">Relationship Type</span>
                    <p className="font-semibold text-teal-400 text-sm uppercase">{inspectedEdge.relationship_type}</p>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">Status:</span>
                    <p className="text-slate-200 mt-0.5">
                      {inspectedEdge.is_documented ? (
                        <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                          Documented Relationship
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                          Graph-Derived Path
                        </span>
                      )}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">Source:</span>
                    <p className="font-mono text-slate-300">{inspectedEdge.source}</p>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">Target:</span>
                    <p className="font-mono text-slate-300">{inspectedEdge.target}</p>
                  </div>
                  {inspectedEdge.evidence && inspectedEdge.evidence.length > 0 && (
                    <div>
                      <span className="text-slate-400 font-medium">Evidence Grounding:</span>
                      {inspectedEdge.evidence.map((ev) => (
                        <div key={ev.id} className="p-2 rounded bg-slate-950 border border-slate-800 mt-1">
                          <p className="font-semibold text-slate-300">
                            {ev.source_database} PMID: {ev.source_record_id}
                          </p>
                          {ev.source_url && (
                            <a
                              href={ev.source_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-emerald-400 hover:underline flex items-center gap-1 mt-1 text-[11px]"
                            >
                              View PubMed Citation <ExternalLink className="w-3 h-3" />
                            </a>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-center text-slate-500 text-xs px-2">
                  <HelpCircle className="w-8 h-8 mb-2 opacity-50" />
                  <p>Click on any node or edge in the graph to inspect biological metadata and literature evidence.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 2: Graph Analysis */}
        {activeTab === "analysis" && graphAnalysis && (
          <div className="space-y-6">
            {/* Summary Banner */}
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-sm text-slate-300 flex items-start gap-3">
              <Activity className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-slate-200">Computational Network Summary:</span>
                <p className="text-xs text-slate-400 mt-1">{graphAnalysis.summary}</p>
              </div>
            </div>

            {/* Centrality Rankings */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <h3 className="font-semibold text-base text-slate-200 mb-3 flex items-center gap-2">
                <Zap className="w-4 h-4 text-emerald-400" />
                Centrality & Connectivity Rankings
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-800 text-slate-400 uppercase text-[10px]">
                    <tr>
                      <th className="py-2.5 px-3">Entity</th>
                      <th className="py-2.5 px-3">Type</th>
                      <th className="py-2.5 px-3">Canonical ID</th>
                      <th className="py-2.5 px-3">Degree Centrality</th>
                      <th className="py-2.5 px-3">Betweenness</th>
                      <th className="py-2.5 px-3">Connectivity Label</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {graphAnalysis.central_nodes.map((node) => (
                      <tr key={node.node_id} className="hover:bg-slate-800/40 transition">
                        <td className="py-2 px-3 font-semibold text-slate-200">{node.name}</td>
                        <td className="py-2 px-3 capitalize text-slate-400">{node.entity_type}</td>
                        <td className="py-2 px-3 font-mono text-slate-400">{node.canonical_id}</td>
                        <td className="py-2 px-3 font-mono text-emerald-400">{node.degree_centrality.toFixed(3)}</td>
                        <td className="py-2 px-3 font-mono text-cyan-400">{node.betweenness_centrality.toFixed(3)}</td>
                        <td className="py-2 px-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                              node.connectivity_label === "high centrality node"
                                ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                                : node.connectivity_label === "highly connected node"
                                ? "bg-teal-500/20 text-teal-300 border-teal-500/30"
                                : "bg-slate-800 text-slate-400 border-slate-700"
                            }`}
                          >
                            {node.connectivity_label}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Direct & Derived Graph Paths */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <h3 className="font-semibold text-base text-slate-200 mb-3 flex items-center gap-2">
                <GitFork className="w-4 h-4 text-emerald-400" />
                Direct & Multi-Hop Path Traversals
              </h3>
              <div className="space-y-2">
                {graphAnalysis.paths.slice(0, 10).map((p, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between text-xs gap-2"
                  >
                    <div className="flex items-center gap-2 flex-wrap">
                      {p.node_names.map((nName, nIdx) => (
                        <React.Fragment key={nIdx}>
                          <span className="font-semibold text-slate-200 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                            {nName}
                          </span>
                          {nIdx < p.node_names.length - 1 && <ArrowRight className="w-3 h-3 text-slate-500" />}
                        </React.Fragment>
                      ))}
                    </div>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border shrink-0 ${
                        p.is_documented_direct
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                          : "bg-purple-500/10 text-purple-400 border-purple-500/20"
                      }`}
                    >
                      {p.is_documented_direct ? "Documented Direct" : `Graph-Derived (${p.length} hops)`}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Pathway & Biological Analysis */}
        {activeTab === "biology" && bioAnalysis && (
          <div className="space-y-6">
            {/* Scientific Note Banner */}
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-400 flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <p>{bioAnalysis.scientific_note}</p>
            </div>

            {/* Reactome Pathways */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <h3 className="font-semibold text-base text-slate-200 mb-3 flex items-center gap-2">
                <Layers className="w-4 h-4 text-amber-400" />
                Reactome Signaling & Metabolic Pathways ({bioAnalysis.connected_pathways.length})
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {bioAnalysis.connected_pathways.map((pw) => (
                  <div key={pw.pathway_id} className="p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <span className="font-semibold text-sm text-slate-200">{pw.name}</span>
                      <span className="font-mono text-[11px] text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20 shrink-0">
                        {pw.canonical_id}
                      </span>
                    </div>
                    <div className="text-xs text-slate-400">
                      <span className="font-medium text-slate-400">Mediating Genes:</span>{" "}
                      <span className="text-slate-200">{pw.mediating_genes.join(", ") || "N/A"}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Gene Ontology Biological Processes */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <h3 className="font-semibold text-base text-slate-200 mb-3 flex items-center gap-2">
                <Dna className="w-4 h-4 text-pink-400" />
                Gene Ontology Biological Processes ({bioAnalysis.connected_processes.length})
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {bioAnalysis.connected_processes.map((bp) => (
                  <div key={bp.process_id} className="p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <span className="font-semibold text-sm text-slate-200">{bp.name}</span>
                      <span className="font-mono text-[11px] text-pink-400 bg-pink-500/10 px-2 py-0.5 rounded border border-pink-500/20 shrink-0">
                        {bp.canonical_id}
                      </span>
                    </div>
                    <div className="text-xs text-slate-400">
                      <span className="font-medium text-slate-400">Associated Genes:</span>{" "}
                      <span className="text-slate-200">{bp.mediating_genes.join(", ") || "N/A"}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Tab 4: Evidence & Provenance */}
        {activeTab === "evidence" && provenanceData && (
          <div className="space-y-6">
            {/* Documented vs Graph-Derived Summary */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30 text-xs space-y-1">
                <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
                  <CheckCircle2 className="w-4 h-4" />
                  Documented Relationships ({provenanceData.total_documented_relationships})
                </div>
                <p className="text-slate-400">
                  Directly grounded by curated scientific literature and PubMed citations.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-purple-950/20 border border-purple-500/30 text-xs space-y-1">
                <div className="flex items-center gap-2 text-purple-400 font-semibold text-sm">
                  <GitFork className="w-4 h-4" />
                  Graph-Derived Insights ({provenanceData.total_graph_derived_relationships})
                </div>
                <p className="text-slate-400">
                  Multi-hop cascade connections mediated through encoding genes and pathways.
                </p>
              </div>
            </div>

            {/* Documented Evidence List */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
              <h3 className="font-semibold text-base text-slate-200">Documented Literature Evidence</h3>
              {provenanceData.documented_evidence.map((item, idx) => (
                <div key={idx} className="p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-slate-200">{item.finding}</span>
                    <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold text-[10px]">
                      DOCUMENTED
                    </span>
                  </div>
                  {item.evidence_records.map((ev) => (
                    <div key={ev.id} className="pt-2 border-t border-slate-800/80 flex items-center justify-between">
                      <span className="text-slate-400">
                        {ev.source_database} • Record ID: {ev.source_record_id} • Type: {ev.evidence_type}
                      </span>
                      {ev.source_url && (
                        <a
                          href={ev.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-emerald-400 hover:underline flex items-center gap-1 font-medium"
                        >
                          PubMed Citation <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 5: Gemini AI Explanation */}
        {activeTab === "gemini" && (
          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-base text-slate-200 flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-amber-400" />
                    Evidence-Grounded Biological Explanation
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Synthesizes verified knowledge graph findings strictly constrained to literature evidence.
                  </p>
                </div>
                <button
                  onClick={handleGenerateExplanation}
                  disabled={isGeneratingExplanation}
                  className="px-4 py-2 bg-gradient-to-r from-amber-500 to-emerald-500 hover:from-amber-400 hover:to-emerald-400 text-slate-950 font-bold text-xs rounded-xl transition shadow-lg disabled:opacity-50 flex items-center gap-2 shrink-0"
                >
                  {isGeneratingExplanation ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-slate-950/30 border-t-slate-950 rounded-full animate-spin" />
                      Synthesizing Knowledge...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-3.5 h-3.5" />
                      Explain Biological Connections
                    </>
                  )}
                </button>
              </div>

              {explanationError && (
                <div className="p-3 rounded-lg bg-red-950/40 border border-red-500/30 text-red-300 text-xs">
                  {explanationError}
                </div>
              )}

              {explanation ? (
                <div className="space-y-4 pt-2">
                  <div className="p-5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300 leading-relaxed space-y-3 prose prose-invert max-w-none">
                    <div className="whitespace-pre-wrap">{explanation.explanation}</div>
                  </div>

                  {/* Highlights Grid */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                    <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 space-y-1.5">
                      <span className="font-semibold text-emerald-400 uppercase tracking-wider text-[10px]">
                        Documented Targets
                      </span>
                      <ul className="space-y-1 list-disc list-inside text-slate-300">
                        {explanation.documented_findings.map((f, i) => (
                          <li key={i}>{f}</li>
                        ))}
                      </ul>
                    </div>

                    <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 space-y-1.5">
                      <span className="font-semibold text-purple-400 uppercase tracking-wider text-[10px]">
                        Graph-Derived Pathways
                      </span>
                      <ul className="space-y-1 list-disc list-inside text-slate-300">
                        {explanation.graph_derived_findings.map((f, i) => (
                          <li key={i}>{f}</li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-[11px] text-slate-400 flex items-start gap-2">
                    <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                    <span>
                      <strong>Scientific Boundary:</strong> {explanation.scientific_limitations} • Model:{" "}
                      <span className="font-mono text-slate-300">{explanation.model_used}</span>
                    </span>
                  </div>
                </div>
              ) : (
                <div className="p-8 rounded-xl bg-slate-950/60 border border-slate-800/80 text-center text-slate-400 text-xs flex flex-col items-center justify-center gap-2">
                  <Sparkles className="w-6 h-6 text-amber-400/60" />
                  <p>Click &quot;Explain Biological Connections&quot; above to generate an evidence-grounded AI synthesis.</p>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950 py-4 text-center text-xs text-slate-500">
        BioNexus Biological Knowledge Discovery Platform • TiDB Cloud • UniProt • Reactome • Gene Ontology • PubMed
      </footer>
    </div>
  );
}
