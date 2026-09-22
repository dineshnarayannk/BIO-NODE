import React from "react";
import { Lightbulb, Target, TrendingUp, Zap } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function KeyInsightsPlaceholder() {
  return (
    <Card className="border-amber-500/20 bg-slate-900/50 relative overflow-hidden">
      <div className="absolute top-0 right-0 w-32 h-32 bg-amber-500/5 rounded-full blur-2xl pointer-events-none" />
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>
            <Lightbulb className="w-5 h-5 text-amber-400" />
            Key Insights
          </CardTitle>
          <Badge variant="warning">Analytical Synthesis</Badge>
        </div>
        <CardDescription>
          Computed bioactivity metrics, hub centrality scores, and primary therapeutic indications.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-2">
            <div className="flex items-center gap-2 text-slate-300 text-xs font-semibold">
              <Target className="w-4 h-4 text-rose-400" />
              Primary Molecular Targets
            </div>
            <p className="text-xs text-slate-400">
              High-confidence enzyme and receptor binding partners identified via bioassays and QSAR modeling.
            </p>
            <div className="pt-2 text-[11px] font-mono text-slate-500">
              Awaiting target scoring engine
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-2">
            <div className="flex items-center gap-2 text-slate-300 text-xs font-semibold">
              <TrendingUp className="w-4 h-4 text-brand-400" />
              Pathway Enrichment
            </div>
            <p className="text-xs text-slate-400">
              Statistical overrepresentation analysis across KEGG & Reactome signaling systems.
            </p>
            <div className="pt-2 text-[11px] font-mono text-slate-500">
              Enrichment pipeline standing by
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-2">
            <div className="flex items-center gap-2 text-slate-300 text-xs font-semibold">
              <Zap className="w-4 h-4 text-accent-400" />
              Mechanism of Action (MoA)
            </div>
            <p className="text-xs text-slate-400">
              Predicted phenotypic mechanism, allosteric inhibition, or transcriptional regulation modes.
            </p>
            <div className="pt-2 text-[11px] font-mono text-slate-500">
              Classification model ready for ML phase
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
