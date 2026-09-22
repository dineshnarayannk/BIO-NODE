import React from "react";
import { BookOpen, ExternalLink, FileText, CheckCircle2 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function EvidencePlaceholder() {
  return (
    <Card className="border-slate-700/50 bg-slate-900/50 relative overflow-hidden">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>
            <BookOpen className="w-5 h-5 text-emerald-400" />
            Evidence & Literature Grounding
          </CardTitle>
          <Badge variant="slate">PubMed / ClinicalTrials.gov</Badge>
        </div>
        <CardDescription>
          Verified scientific citations, assay data, and peer-reviewed experimental literature validating network edges.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-3">
          <div className="flex items-center gap-2 text-xs text-slate-300 font-medium">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            Evidence Verification Framework
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Every biological association in BioNexus is tied directly to peer-reviewed literature (PMIDs) or verified biochemical assay databases. No speculative edges are displayed without explicit provenance.
          </p>

          <div className="mt-3 p-3 rounded-lg bg-slate-900/80 border border-slate-800/60 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2 text-slate-400">
              <FileText className="w-4 h-4 text-slate-500" />
              <span>Evidence Indexing Module</span>
            </div>
            <span className="font-mono text-[11px] text-slate-500">
              PubMed API & TiDB Store (Pending)
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
