import React from "react";
import { FlaskConical, Atom, Hash, ExternalLink, Dna } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CompoundSummary } from "@/types";

interface Props {
  selectedCompound?: string | null;
  compoundData?: CompoundSummary | null;
}

export function CompoundOverviewPlaceholder({ selectedCompound, compoundData }: Props) {
  const hasRealData = !!compoundData;

  return (
    <Card className="border-brand-500/20 bg-slate-900/50 relative overflow-hidden">
      <div className="absolute top-0 right-0 w-32 h-32 bg-brand-500/5 rounded-full blur-2xl pointer-events-none" />
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>
            <FlaskConical className="w-5 h-5 text-brand-400" />
            Compound Overview
          </CardTitle>
          <Badge variant={hasRealData ? "brand" : "slate"}>
            {hasRealData ? "StreptomeDB Ingested" : "Chemical Identity"}
          </Badge>
        </div>
        <CardDescription>
          Molecular formula, canonical identifier, SMILES notation, and physicochemical properties.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {selectedCompound ? (
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <span className="text-[10px] text-slate-500 uppercase tracking-wider font-mono">
                  Natural Compound Name
                </span>
                <p className="text-base font-bold text-white">
                  {compoundData?.name || selectedCompound}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {compoundData?.canonical_id && (
                  <Badge variant="accent" className="font-mono text-xs">
                    {compoundData.canonical_id}
                  </Badge>
                )}
                {compoundData?.pubchem_cid && (
                  <a
                    href={`https://pubchem.ncbi.nlm.nih.gov/compound/${compoundData.pubchem_cid}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-[11px] text-brand-300 hover:text-brand-200 px-2 py-0.5 rounded bg-brand-500/10 border border-brand-500/20"
                  >
                    PubChem: {compoundData.pubchem_cid}
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
              <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800/50">
                <span className="text-[11px] text-slate-400">Canonical ID</span>
                <p className="text-xs font-mono text-slate-200 mt-0.5">
                  {compoundData?.canonical_id || "Awaiting match"}
                </p>
              </div>
              <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800/50">
                <span className="text-[11px] text-slate-400">Molecular Weight</span>
                <p className="text-xs font-mono text-slate-200 mt-0.5">
                  {compoundData?.molecular_weight
                    ? `${compoundData.molecular_weight.toFixed(2)} g/mol`
                    : "— g/mol"}
                </p>
              </div>
              <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800/50">
                <span className="text-[11px] text-slate-400">Data Source</span>
                <p className="text-xs font-mono text-brand-300 truncate mt-0.5">
                  {compoundData?.source || "TiDB Knowledge Base"}
                </p>
              </div>
            </div>

            {compoundData?.smiles && (
              <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800/50 space-y-1">
                <span className="text-[10px] text-slate-400 uppercase tracking-wider font-mono">
                  Canonical SMILES
                </span>
                <p className="text-xs font-mono text-slate-300 break-all leading-relaxed select-all">
                  {compoundData.smiles}
                </p>
              </div>
            )}
          </div>
        ) : null}

        {/* 2D/3D Molecular Structure Visualization Stub */}
        <div className="h-44 rounded-xl border border-dashed border-slate-800 bg-slate-950/40 flex flex-col items-center justify-center p-6 text-center space-y-2">
          <Atom className="w-8 h-8 text-brand-400/60 animate-spin" style={{ animationDuration: "20s" }} />
          <p className="text-xs font-medium text-slate-300">Molecular Structure Renderer (RDKit / 3D Canvas)</p>
          <p className="text-[11px] text-slate-500 max-w-sm">
            {hasRealData
              ? "Chemical topology loaded from StreptomeDB. Interactive 2D/3D conformation viewer will render in visualization phase."
              : "Will render interactive 2D Lewis structures and 3D conformations upon data search."}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
