import React from "react";
import { Sparkles, Bot, ShieldCheck, Quote } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function AIExplanationPlaceholder() {
  return (
    <Card className="border-brand-400/30 bg-gradient-to-br from-slate-900/80 via-slate-900/40 to-brand-950/20 relative overflow-hidden">
      <div className="absolute top-0 right-0 w-48 h-48 bg-brand-500/10 rounded-full blur-3xl pointer-events-none" />
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>
            <Sparkles className="w-5 h-5 text-brand-300 animate-pulse" />
            AI Biological Explanation
          </CardTitle>
          <Badge variant="brand">Grounded LLM Reasoning</Badge>
        </div>
        <CardDescription>
          Contextual hypothesis generation and natural language synthesis strictly constrained to retrieved evidence and graph topology.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="p-5 rounded-xl bg-slate-950/70 border border-brand-500/20 space-y-3 relative">
          <div className="flex items-center gap-2 text-xs font-semibold text-brand-300">
            <Bot className="w-4 h-4 text-brand-400" />
            Evidence-Grounded Synthesizer
          </div>
          <p className="text-xs text-slate-300 leading-relaxed italic">
            &ldquo;When enabled in future phases, the BioNexus reasoning engine will synthesize mechanistic summaries connecting the query compound to disease phenotypes, explicitly tagging every assertion with retrieved subgraph paths and PubMed citations to prevent hallucination.&rdquo;
          </p>

          <div className="pt-2 flex flex-wrap items-center gap-3 text-[11px] text-slate-400 border-t border-slate-800/80">
            <span className="flex items-center gap-1 text-brand-400/90 font-mono">
              <ShieldCheck className="w-3.5 h-3.5" /> Hallucination Guardrails: Active
            </span>
            <span>•</span>
            <span className="font-mono text-slate-500">
              Provider: Gemini / OpenAI (Pending API Key)
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
