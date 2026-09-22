"use client";

import React, { useEffect, useRef, useState } from "react";
import cytoscape, { Core, EventObject } from "cytoscape";
import { CompoundGraphResponse, GraphEdge, GraphNode } from "@/types";
import { Maximize2, Minus, Plus, RefreshCw } from "lucide-react";

interface CytoscapeGraphProps {
  graphData: CompoundGraphResponse;
  onNodeSelect?: (node: GraphNode | null) => void;
  onEdgeSelect?: (edge: GraphEdge | null) => void;
}

const ENTITY_COLORS: Record<string, string> = {
  compound: "#10b981", // Emerald
  protein: "#3b82f6", // Blue
  gene: "#8b5cf6", // Violet
  pathway: "#f59e0b", // Amber
  biological_process: "#ec4899", // Pink
};

export default function CytoscapeGraph({
  graphData,
  onNodeSelect,
  onEdgeSelect,
}: CytoscapeGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [layoutName, setLayoutName] = useState<"breadthfirst" | "cose" | "concentric">("breadthfirst");
  const [selectedEntity, setSelectedEntity] = useState<string>("all");

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
      ...visibleNodes.map((node) => ({
        group: "nodes" as const,
        data: {
          id: node.id,
          label: node.name.length > 22 ? `${node.name.slice(0, 20)}...` : node.name,
          fullName: node.name,
          canonical_id: node.canonical_id,
          entity_type: node.entity_type,
          bgColor: ENTITY_COLORS[node.entity_type] || "#64748b",
          rawNode: node,
        },
      })),
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
        {
          selector: "node",
          style: {
            "background-color": "data(bgColor)",
            label: "data(label)",
            color: "#ffffff",
            "font-size": "11px",
            "font-weight": 600,
            "text-valign": "bottom",
            "text-margin-y": 6,
            "text-background-opacity": 0.85,
            "text-background-color": "#0f172a",
            "text-background-padding": "3px",
            "text-background-shape": "roundrectangle",
            width: "36px",
            height: "36px",
            "border-width": 2,
            "border-color": "#ffffff",
            "border-opacity": 0.9,
            "transition-property": "background-color, border-color, width, height",
            "transition-duration": 0.2,
          },
        },
        {
          selector: 'node[entity_type = "compound"]',
          style: {
            width: "48px",
            height: "48px",
            "font-size": "13px",
            "font-weight": 700,
            "border-width": 3,
            "border-color": "#a7f3d0",
          },
        },
        {
          selector: "node:selected",
          style: {
            "border-width": 4,
            "border-color": "#38bdf8",
            "border-opacity": 1,
            width: "44px",
            height: "44px",
          },
        },
        {
          selector: "edge",
          style: {
            width: 2.5,
            "line-color": "#64748b",
            "target-arrow-color": "#64748b",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "arrow-scale": 1.2,
            label: "data(label)",
            "font-size": "9px",
            "font-weight": 500,
            color: "#94a3b8",
            "text-background-opacity": 0.8,
            "text-background-color": "#0f172a",
            "text-background-padding": "2px",
            "text-rotation": "autorotate",
            "text-margin-y": -6,
          },
        },
        {
          selector: "edge:selected",
          style: {
            width: 4,
            "line-color": "#38bdf8",
            "target-arrow-color": "#38bdf8",
            color: "#38bdf8",
          },
        },
      ],
      layout: {
        name: layoutName,
        directed: true,
        padding: 40,
        spacingFactor: 1.3,
        animate: true,
        animationDuration: 400,
      },
    });

    cy.on("tap", "node", (evt: EventObject) => {
      const node = evt.target;
      const rawNode = node.data("rawNode") as GraphNode;
      if (onNodeSelect) onNodeSelect(rawNode);
    });

    cy.on("tap", "edge", (evt: EventObject) => {
      const edge = evt.target;
      const rawEdge = edge.data("rawEdge") as GraphEdge;
      if (onEdgeSelect) onEdgeSelect(rawEdge);
    });

    cy.on("tap", (evt: EventObject) => {
      if (evt.target === cy) {
        if (onNodeSelect) onNodeSelect(null);
        if (onEdgeSelect) onEdgeSelect(null);
      }
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
    };
  }, [graphData, layoutName, selectedEntity, onNodeSelect, onEdgeSelect]);

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
      cyRef.current.fit(undefined, 30);
    }
  };

  return (
    <div className="relative w-full h-[520px] rounded-xl overflow-hidden bg-slate-950 border border-slate-800 shadow-2xl flex flex-col">
      {/* Top Controls Toolbar */}
      <div className="flex flex-wrap items-center justify-between px-4 py-2.5 bg-slate-900/80 backdrop-blur-md border-b border-slate-800 text-xs text-slate-300 z-10 gap-2">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-slate-400">Filter Layer:</span>
          <select
            value={selectedEntity}
            onChange={(e) => setSelectedEntity(e.target.value)}
            className="bg-slate-800 border border-slate-700 text-slate-200 rounded px-2.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500"
          >
            <option value="all">All Entities</option>
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
            <option value="concentric">Concentric</option>
          </select>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-1.5">
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
                cyRef.current.layout({ name: layoutName, directed: true, padding: 40, animate: true }).run();
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
      <div ref={containerRef} className="w-full flex-1 bg-gradient-to-b from-slate-950 to-slate-900" />

      {/* Bottom Legend */}
      <div className="flex flex-wrap items-center justify-center gap-4 px-3 py-2 bg-slate-900/90 border-t border-slate-800 text-[11px] text-slate-400">
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
    </div>
  );
}
