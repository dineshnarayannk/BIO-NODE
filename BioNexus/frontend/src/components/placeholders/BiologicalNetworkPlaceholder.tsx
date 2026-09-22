import React from "react";
import { GitGraph, Network, Maximize2, Share2, Filter } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function BiologicalNetworkPlaceholder() {
  return (
    <Card className="border-accent-500/20 bg-slate-900/50 relative overflow-hidden">
      <div className="absolute top-0 right-0 w-36 h-36 bg-accent-500/5 rounded-full blur-2xl pointer-events-none" />
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>
            <Network className="w-5 h-5 text-accent-400" />
            Biological Network
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="accent">Cytoscape.js Ready</Badge>
          </div>
        </div>
        <CardDescription>
          Multi-scale knowledge graph mapping compound-target bindings, downstream signaling cascades, and pathway crosstalk.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-64 sm:h-80 rounded-xl border border-dashed border-slate-800 bg-slate-950/60 relative flex flex-col items-center justify-center p-6 text-center overflow-hidden">
          {/* Simulated Graph Nodes & Links background effect */}
          <div className="absolute inset-0 opacity-15 pointer-events-none flex items-center justify-center">
            <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
              <line x1="20%" y1="30%" x2="50%" y2="50%" stroke="#22d3ee" strokeWidth="1.5" strokeDasharray="4 4" />
              <line x1="80%" y1="25%" x2="50%" y2="50%" stroke="#10b981" strokeWidth="1.5" strokeDasharray="4 4" />
              <line x1="50%" y1="50%" x2="35%" y2="80%" stroke="#38bdf8" strokeWidth="1.5" />
              <line x1="50%" y1="50%" x2="70%" y2="75%" stroke="#a855f7" strokeWidth="1.5" />
              <circle cx="50%" cy="50%" r="22" fill="#0f172a" stroke="#22d3ee" strokeWidth="2" />
              <circle cx="20%" cy="30%" r="14" fill="#0f172a" stroke="#10b981" strokeWidth="2" />
              <circle cx="80%" cy="25%" r="14" fill="#0f172a" stroke="#a855f7" strokeWidth="2" />
              <circle cx="35%" cy="80%" r="16" fill="#0f172a" stroke="#38bdf8" strokeWidth="2" />
              <circle cx="70%" cy="75%" r="15" fill="#0f172a" stroke="#eab308" strokeWidth="2" />
            </svg>
          </div>

          <div className="relative z-10 max-w-md space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-accent-500/10 border border-accent-500/30 flex items-center justify-center mx-auto text-accent-400">
              <GitGraph className="w-6 h-6 animate-pulse" />
            </div>
            <h4 className="text-sm font-semibold text-slate-200">Interactive Knowledge Graph Canvas</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              NetworkX graph traversals and Cytoscape.js rendering pipeline will visualize compound targets (UniProt), modulated genes, and enriched biological pathways (Reactome/KEGG).
            </p>
            <div className="flex items-center justify-center gap-2 pt-2">
              <span className="inline-flex items-center gap-1 text-[11px] font-mono px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-400">
                <span className="w-2 h-2 rounded-full bg-emerald-400" /> Compound
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] font-mono px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-400">
                <span className="w-2 h-2 rounded-full bg-cyan-400" /> Protein Target
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] font-mono px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-400">
                <span className="w-2 h-2 rounded-full bg-purple-400" /> Biological Pathway
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
