"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import cytoscape, { Core, EventObject, NodeSingular, EdgeSingular } from "cytoscape";
import { CompoundGraphResponse, GraphEdge, GraphNode } from "@/types";
import {
  Activity,
  CheckCircle2,
  Database,
  Dna,
  Eye,
  GitBranch,
  Info,
  Maximize2,
  Minus,
  Play,
  Plus,
  RefreshCw,
  Sparkles,
  Zap,
} from "lucide-react";

interface CytoscapeGraphProps {
  graphData: CompoundGraphResponse;
  onNodeSelect?: (node: GraphNode | null) => void;
  onEdgeSelect?: (edge: GraphEdge | null) => void;
}

const ENTITY_CONFIG: Record<
  string,
  { label: string; color: string; bgSoft: string; borderColor: string; icon: string; size: number }
> = {
  compound: {
    label: "Compound",
    color: "#10b981", // Emerald
    bgSoft: "rgba(16, 185, 129, 0.15)",
    borderColor: "#34d399",
    icon: "🧪",
    size: 48,
  },
  protein: {
    label: "Protein",
    color: "#3b82f6", // Blue
    bgSoft: "rgba(59, 130, 246, 0.15)",
    borderColor: "#60a5fa",
    icon: "🧬",
    size: 40,
  },
  gene: {
    label: "Gene",
    color: "#8b5cf6", // Violet
    bgSoft: "rgba(139, 92, 246, 0.15)",
    borderColor: "#a78bfa",
    icon: "🔬",
    size: 38,
  },
  pathway: {
    label: "Pathway",
    color: "#f59e0b", // Amber
    bgSoft: "rgba(245, 158, 11, 0.15)",
    borderColor: "#fbbf24",
    icon: "🛤",
    size: 38,
  },
  biological_process: {
    label: "Biological Process",
    color: "#ec4899", // Pink
    bgSoft: "rgba(236, 72, 153, 0.15)",
    borderColor: "#f472b6",
    icon: "⚡",
    size: 38,
  },
};

// Hierarchy order for progressive reveal animation
const ENTITY_REVEAL_ORDER: Array<{ type: GraphNode["entity_type"]; phaseName: string; delay: number }> = [
  { type: "compound", phaseName: "Natural Metabolite", delay: 0 },
  { type: "protein", phaseName: "Protein Targets", delay: 350 },
  { type: "gene", phaseName: "Encoding Genes", delay: 700 },
  { type: "pathway", phaseName: "Reactome Pathways", delay: 1050 },
  { type: "biological_process", phaseName: "GO Biological Processes", delay: 1400 },
];

export default function CytoscapeGraph({
  graphData,
  onNodeSelect,
  onEdgeSelect,
}: CytoscapeGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const timeoutsRef = useRef<NodeJS.Timeout[]>([]);

  const [layoutName, setLayoutName] = useState<"breadthfirst" | "cose" | "concentric">("breadthfirst");
  const [selectedEntity, setSelectedEntity] = useState<string>("all");
  const [isAnimating, setIsAnimating] = useState(false);
  const [currentPhase, setCurrentPhase] = useState<string | null>(null);

  // Track which compounds have already had their reveal animation executed
  const animatedCompoundIdsRef = useRef<Set<string>>(new Set());

  // Hover Tooltip State
  const [hoveredNode, setHoveredNode] = useState<{
    node: GraphNode;
    x: number;
    y: number;
  } | null>(null);

  // Clear all pending animation timeouts
  const clearAnimationTimeouts = useCallback(() => {
    timeoutsRef.current.forEach((t) => clearTimeout(t));
    timeoutsRef.current = [];
  }, []);

  // Run the progressive reveal animation sequence
  const runProgressiveReveal = useCallback(
    (cy: Core) => {
      clearAnimationTimeouts();

      // Check prefers-reduced-motion
      const prefersReducedMotion =
        typeof window !== "undefined" &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;

      if (prefersReducedMotion) {
        cy.elements().removeClass("hidden-element").addClass("revealed-element");
        setIsAnimating(false);
        setCurrentPhase(null);
        return;
      }

      setIsAnimating(true);

      // Hide all elements initially
      cy.elements().addClass("hidden-element").removeClass("revealed-element phase-active");

      // Progressively reveal by entity hierarchy
      ENTITY_REVEAL_ORDER.forEach((phase, index) => {
        const t = setTimeout(() => {
          if (!cy || cy.destroyed()) return;

          setCurrentPhase(phase.phaseName);

          cy.batch(() => {
            // Find nodes of this entity type
            const currentNodes = cy.nodes(`[entity_type = "${phase.type}"]`);
            currentNodes.removeClass("hidden-element").addClass("revealed-element phase-active");

            // Reveal connected edges where both source and target are now revealed
            cy.edges().forEach((edge) => {
              const src = edge.source();
              const tgt = edge.target();
              if (src.hasClass("revealed-element") && tgt.hasClass("revealed-element")) {
                edge.removeClass("hidden-element").addClass("revealed-element");
              }
            });
          });

          // Soft pulse/scale transition for newly revealed nodes
          const newlyRevealed = cy.nodes(`[entity_type = "${phase.type}"]`);
          newlyRevealed.forEach((n) => {
            n.animate(
              {
                style: {
                  "border-width": phase.type === "compound" ? 5 : 3.5,
                  "border-opacity": 1,
                },
              },
              {
                duration: 250,
                complete: () => {
                  n.animate(
                    {
                      style: {
                        "border-width": phase.type === "compound" ? 3.5 : 2,
                        "border-opacity": 0.9,
                      },
                    },
                    { duration: 200 }
                  );
                },
              }
            );
          });

          // End of all phases
          if (index === ENTITY_REVEAL_ORDER.length - 1) {
            const finalTimeout = setTimeout(() => {
              if (cy && !cy.destroyed()) {
                cy.elements().removeClass("phase-active");
                setIsAnimating(false);
                setCurrentPhase(null);
                cy.animate({
                  fit: { eles: cy.elements(), padding: 35 },
                  duration: 350,
                });
              }
            }, 450);
            timeoutsRef.current.push(finalTimeout);
          }
        }, phase.delay);

        timeoutsRef.current.push(t);
      });
    },
    [clearAnimationTimeouts]
  );

  // Initialize and update Cytoscape
  useEffect(() => {
    if (!containerRef.current || !graphData || graphData.nodes.length === 0) return;

    // Filter elements if selectedEntity is not "all"
    const visibleNodes =
      selectedEntity === "all"
        ? graphData.nodes
        : graphData.nodes.filter(
            (n) => n.entity_type === selectedEntity || n.entity_type === "compound"
          );

    const visibleNodeIds = new Set(visibleNodes.map((n) => n.id));

    const visibleEdges = graphData.edges.filter(
      (e) => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target)
    );

    const elements: cytoscape.ElementDefinition[] = [
      ...visibleNodes.map((node) => {
        const config = ENTITY_CONFIG[node.entity_type] || ENTITY_CONFIG.compound;
        return {
          group: "nodes" as const,
          data: {
            id: node.id,
            label: node.name.length > 20 ? `${node.name.slice(0, 18)}...` : node.name,
            fullName: node.name,
            canonical_id: node.canonical_id,
            entity_type: node.entity_type,
            bgColor: config.color,
            borderColor: config.borderColor,
            nodeSize: config.size,
            icon: config.icon,
            rawNode: node,
          },
        };
      }),
      ...visibleEdges.map((edge) => ({
        group: "edges" as const,
        data: {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          label: edge.relationship_type.replace(/_/g, " "),
          relationship_type: edge.relationship_type,
          is_documented: edge.is_documented,
          rawEdge: edge,
        },
      })),
    ];

    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        // Base Node Style
        {
          selector: "node",
          style: {
            "background-color": "data(bgColor)",
            label: "data(label)",
            color: "#ffffff",
            "font-size": "10.5px",
            "font-weight": 600,
            "text-valign": "bottom",
            "text-margin-y": 6,
            "text-background-opacity": 0.9,
            "text-background-color": "#090d16",
            "text-background-padding": "3px",
            "text-background-shape": "roundrectangle",
            width: "data(nodeSize)",
            height: "data(nodeSize)",
            "border-width": 2,
            "border-color": "data(borderColor)",
            "border-opacity": 0.85,
            "transition-property":
              "background-color, border-color, border-width, border-opacity, width, height, opacity",
            "transition-duration": 0.25,
            opacity: 1,
          },
        },
        // Root Compound Node (Hero Visual)
        {
          selector: 'node[entity_type = "compound"]',
          style: {
            width: "48px",
            height: "48px",
            "font-size": "12px",
            "font-weight": 700,
            "border-width": 3.5,
            "border-color": "#6ee7b7",
            "border-opacity": 1,
            "text-background-color": "#064e3b",
          },
        },
        // Protein Nodes
        {
          selector: 'node[entity_type = "protein"]',
          style: {
            "border-color": "#93c5fd",
          },
        },
        // Gene Nodes
        {
          selector: 'node[entity_type = "gene"]',
          style: {
            "border-color": "#c4b5fd",
          },
        },
        // Pathway Nodes
        {
          selector: 'node[entity_type = "pathway"]',
          style: {
            "border-color": "#fde68a",
          },
        },
        // Biological Process Nodes
        {
          selector: 'node[entity_type = "biological_process"]',
          style: {
            "border-color": "#fbcfe8",
          },
        },

        // Base Edge Style (Documented Relationships)
        {
          selector: "edge",
          style: {
            width: 2.5,
            "line-color": "#475569",
            "target-arrow-color": "#475569",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "arrow-scale": 1.1,
            label: "data(label)",
            "font-size": "8.5px",
            "font-weight": 500,
            color: "#94a3b8",
            "text-background-opacity": 0.85,
            "text-background-color": "#090d16",
            "text-background-padding": "2px",
            "text-rotation": "autorotate",
            "text-margin-y": -6,
            "transition-property": "line-color, target-arrow-color, width, opacity",
            "transition-duration": 0.25,
            opacity: 0.9,
          },
        },

        // Documented Edge Styling (Solid Line, Direct Empirical Evidence)
        {
          selector: "edge[?is_documented]",
          style: {
            "line-color": "#0ea5e9",
            "target-arrow-color": "#0ea5e9",
            width: 2.5,
            "line-style": "solid",
          },
        },

        // Graph-Derived Edge Styling (Dashed Line, Inferred Cascade)
        {
          selector: "edge[!is_documented]",
          style: {
            "line-color": "#64748b",
            "target-arrow-color": "#64748b",
            width: 2.0,
            "line-style": "dashed",
            "line-dash-pattern": [6, 3],
          },
        },

        // Hidden elements during progressive reveal
        {
          selector: ".hidden-element",
          style: {
            opacity: 0,
            "display": "none",
          },
        },
        // Revealed elements
        {
          selector: ".revealed-element",
          style: {
            "display": "element",
            opacity: 1,
          },
        },

        // Hovered Node State
        {
          selector: "node.hovered-node",
          style: {
            "border-width": 4,
            "border-color": "#38bdf8",
            "border-opacity": 1,
            width: "52px",
            height: "52px",
          },
        },
        // Highlighted Neighbors on Hover / Selection
        {
          selector: "node.highlighted-neighbor",
          style: {
            "border-width": 3.5,
            "border-color": "#38bdf8",
            "border-opacity": 1,
            opacity: 1,
          },
        },
        {
          selector: "edge.highlighted-edge",
          style: {
            width: 4,
            "line-color": "#38bdf8",
            "target-arrow-color": "#38bdf8",
            color: "#38bdf8",
            opacity: 1,
          },
        },

        // Dimmed Elements (Unfocused)
        {
          selector: ".dimmed",
          style: {
            opacity: 0.18,
          },
        },

        // Selected Node State
        {
          selector: "node:selected",
          style: {
            "border-width": 4.5,
            "border-color": "#38bdf8",
            "border-opacity": 1,
            width: "50px",
            height: "50px",
          },
        },
        // Selected Edge State
        {
          selector: "edge:selected",
          style: {
            width: 4.5,
            "line-color": "#38bdf8",
            "target-arrow-color": "#38bdf8",
            color: "#38bdf8",
            opacity: 1,
          },
        },
      ],
      layout: {
        name: layoutName,
        directed: true,
        padding: 40,
        spacingFactor: 1.3,
        animate: false,
      },
    });

    // Node Hover Interactions
    cy.on("mouseover", "node", (evt: EventObject) => {
      const node = evt.target as NodeSingular;
      const rawNode = node.data("rawNode") as GraphNode;

      // Dim unrelated nodes and highlight neighborhood
      cy.batch(() => {
        cy.elements().addClass("dimmed");
        node.removeClass("dimmed").addClass("hovered-node");

        const neighborhood = node.neighborhood();
        neighborhood.nodes().removeClass("dimmed").addClass("highlighted-neighbor");
        neighborhood.edges().removeClass("dimmed").addClass("highlighted-edge");
      });

      // Position tooltip near cursor
      const renderedPos = node.renderedPosition();
      const containerBox = containerRef.current?.getBoundingClientRect();
      if (containerBox) {
        setHoveredNode({
          node: rawNode,
          x: Math.min(Math.max(renderedPos.x, 100), containerBox.width - 240),
          y: Math.max(renderedPos.y - 70, 10),
        });
      }
    });

    cy.on("mouseout", "node", () => {
      cy.batch(() => {
        cy.elements().removeClass("dimmed hovered-node highlighted-neighbor highlighted-edge");
      });
      setHoveredNode(null);
    });

    // Click / Selection Interactions
    cy.on("tap", "node", (evt: EventObject) => {
      const node = evt.target as NodeSingular;
      const rawNode = node.data("rawNode") as GraphNode;

      cy.batch(() => {
        cy.elements().removeClass("dimmed hovered-node highlighted-neighbor highlighted-edge");
        cy.elements().addClass("dimmed");
        node.removeClass("dimmed");

        const neighborhood = node.neighborhood();
        neighborhood.nodes().removeClass("dimmed").addClass("highlighted-neighbor");
        neighborhood.edges().removeClass("dimmed").addClass("highlighted-edge");
      });

      if (onNodeSelect) onNodeSelect(rawNode);
    });

    cy.on("tap", "edge", (evt: EventObject) => {
      const edge = evt.target as EdgeSingular;
      const rawEdge = edge.data("rawEdge") as GraphEdge;

      cy.batch(() => {
        cy.elements().removeClass("dimmed hovered-node highlighted-neighbor highlighted-edge");
        cy.elements().addClass("dimmed");
        edge.removeClass("dimmed").addClass("highlighted-edge");
        edge.source().removeClass("dimmed").addClass("highlighted-neighbor");
        edge.target().removeClass("dimmed").addClass("highlighted-neighbor");
      });

      if (onEdgeSelect) onEdgeSelect(rawEdge);
    });

    cy.on("tap", (evt: EventObject) => {
      if (evt.target === cy) {
        cy.batch(() => {
          cy.elements().removeClass("dimmed hovered-node highlighted-neighbor highlighted-edge");
        });
        if (onNodeSelect) onNodeSelect(null);
        if (onEdgeSelect) onEdgeSelect(null);
      }
    });

    cyRef.current = cy;

    // Identify compound key to run reveal animation only on the initial load
    const compoundKey =
      graphData.compound?.id ||
      graphData.compound?.canonical_id ||
      graphData.nodes.find((n) => n.entity_type === "compound")?.id ||
      "compound_initial";

    const isFirstTime = !animatedCompoundIdsRef.current.has(compoundKey);

    if (isFirstTime) {
      animatedCompoundIdsRef.current.add(compoundKey);
      runProgressiveReveal(cy);
    } else {
      // If already animated previously, display graph immediately without repeating animation
      cy.elements().removeClass("hidden-element").addClass("revealed-element");
      setIsAnimating(false);
      setCurrentPhase(null);
      cy.layout({
        name: layoutName,
        directed: true,
        padding: 35,
        spacingFactor: 1.3,
        animate: false,
      }).run();
      cy.fit(undefined, 35);
    }

    return () => {
      clearAnimationTimeouts();
      cy.destroy();
    };
  }, [graphData, layoutName, selectedEntity, onNodeSelect, onEdgeSelect, runProgressiveReveal, clearAnimationTimeouts]);

  const handleZoomIn = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 1.25);
    }
  };

  const handleZoomOut = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 0.8);
    }
  };

  const handleFit = () => {
    if (cyRef.current) {
      cyRef.current.fit(undefined, 35);
    }
  };

  const handleReplayAnimation = () => {
    if (cyRef.current && !isAnimating) {
      runProgressiveReveal(cyRef.current);
    }
  };

  return (
    <div className="relative w-full h-[520px] rounded-xl overflow-hidden bg-slate-950 border border-slate-800 shadow-2xl flex flex-col">
      {/* Top Controls Toolbar */}
      <div className="flex flex-wrap items-center justify-between px-4 py-2 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 text-xs text-slate-300 z-10 gap-2">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-slate-400">Filter Layer:</span>
          <select
            value={selectedEntity}
            onChange={(e) => setSelectedEntity(e.target.value)}
            className="bg-slate-800 border border-slate-700 text-slate-200 rounded px-2.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500"
          >
            <option value="all">All Entities ({graphData.nodes.length})</option>
            <option value="protein">Proteins Only</option>
            <option value="gene">Genes Only</option>
            <option value="pathway">Pathways Only</option>
            <option value="biological_process">Processes Only</option>
          </select>

          <span className="font-semibold text-slate-400 ml-2">Layout:</span>
          <select
            value={layoutName}
            onChange={(e) => setLayoutName(e.target.value as any)}
            className="bg-slate-800 border border-slate-700 text-slate-200 rounded px-2.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500"
          >
            <option value="breadthfirst">Hierarchical (Breadthfirst)</option>
            <option value="cose">Force-Directed (CoSE)</option>
            <option value="concentric">Concentric Circles</option>
          </select>
        </div>

        {/* Action buttons & Animation Status */}
        <div className="flex items-center gap-1.5">
          {/* Progressive Reveal Indicator */}
          {isAnimating && currentPhase && (
            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-[11px] font-medium animate-pulse">
              <Sparkles className="w-3 h-3" />
              <span>Revealing {currentPhase}...</span>
            </div>
          )}

          {/* Replay Animation Button */}
          <button
            onClick={handleReplayAnimation}
            disabled={isAnimating}
            title="Replay Biological Graph Reveal"
            className="flex items-center gap-1 px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-emerald-300 rounded border border-slate-700 transition disabled:opacity-50 text-[11px]"
          >
            <Play className="w-3 h-3 text-emerald-400 fill-emerald-400" />
            <span className="hidden md:inline">Replay Reveal</span>
          </button>

          <button
            onClick={handleZoomIn}
            title="Zoom In"
            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 transition"
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleZoomOut}
            title="Zoom Out"
            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 transition"
          >
            <Minus className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleFit}
            title="Fit to Screen"
            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 transition"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => {
              if (cyRef.current) {
                cyRef.current.layout({ name: layoutName, directed: true, padding: 35, animate: true }).run();
              }
            }}
            title="Reset Layout"
            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Cytoscape Canvas Container */}
      <div ref={containerRef} className="w-full flex-1 bg-gradient-to-b from-slate-950 via-slate-950/90 to-slate-900 relative" />

      {/* Interactive Floating Hover Tooltip */}
      {hoveredNode && (
        <div
          className="absolute z-30 pointer-events-none p-3 rounded-xl bg-slate-900/95 border border-slate-700 shadow-2xl backdrop-blur-md text-xs space-y-1.5 min-w-[210px] max-w-[280px] transition-all duration-150"
          style={{
            left: `${hoveredNode.x}px`,
            top: `${hoveredNode.y}px`,
          }}
        >
          <div className="flex items-center justify-between gap-2 border-b border-slate-800 pb-1.5">
            <div className="flex items-center gap-1.5 truncate">
              <span>{ENTITY_CONFIG[hoveredNode.node.entity_type]?.icon || "🔬"}</span>
              <span className="font-bold text-white text-xs truncate">{hoveredNode.node.name}</span>
            </div>
            <span
              className="text-[10px] uppercase px-1.5 py-0.5 rounded font-bold"
              style={{
                backgroundColor: ENTITY_CONFIG[hoveredNode.node.entity_type]?.bgSoft || "rgba(100,116,139,0.2)",
                color: ENTITY_CONFIG[hoveredNode.node.entity_type]?.color || "#94a3b8",
              }}
            >
              {hoveredNode.node.entity_type.replace("_", " ")}
            </span>
          </div>

          <div className="text-[11px] text-slate-300 space-y-0.5">
            <div>
              <span className="text-slate-500 font-medium">Canonical ID: </span>
              <span className="font-mono text-emerald-400 font-semibold">{hoveredNode.node.canonical_id}</span>
            </div>
            {hoveredNode.node.metadata?.pubchem_cid && (
              <div>
                <span className="text-slate-500 font-medium">PubChem CID: </span>
                <span className="text-cyan-400">{hoveredNode.node.metadata.pubchem_cid}</span>
              </div>
            )}
            {hoveredNode.node.metadata?.molecular_weight && (
              <div>
                <span className="text-slate-500 font-medium">Mol Wt: </span>
                <span className="text-slate-200">{hoveredNode.node.metadata.molecular_weight.toFixed(2)} g/mol</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Bottom Legend & Provenance Distinction */}
      <div className="flex flex-wrap items-center justify-between gap-4 px-4 py-2 bg-slate-900/90 border-t border-slate-800 text-[11px] text-slate-400">
        {/* Node Types Legend */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
            <span>Compound</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
            <span>Protein</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-violet-500" />
            <span>Gene</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
            <span>Pathway</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-pink-500" />
            <span>Biological Process</span>
          </div>
        </div>

        {/* Edge Provenance Distinction */}
        <div className="flex items-center gap-3 border-l border-slate-800 pl-3">
          <div className="flex items-center gap-1.5" title="Direct empirical evidence in scientific databases">
            <span className="w-4 h-0.5 bg-sky-400 inline-block" />
            <span className="text-sky-300 font-medium text-[10px]">Documented</span>
          </div>
          <div className="flex items-center gap-1.5" title="Inferred biological cascade connection">
            <span className="w-4 h-0.5 border-t border-dashed border-slate-400 inline-block" />
            <span className="text-slate-400 font-medium text-[10px]">Graph Derived</span>
          </div>
        </div>
      </div>
    </div>
  );
}
