import React from "react";
import { Sparkles, Database, GitBranch, Cpu } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-slate-900 bg-slate-950/80 mt-20 py-12 text-slate-500 text-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex flex-col sm:flex-row items-center gap-3 text-center sm:text-left">
          <span className="font-semibold text-slate-400 font-heading">
            BioNexus Discovery Engine
          </span>
          <span className="hidden sm:inline text-slate-700">•</span>
          <span>Next.js • FastAPI • TiDB Cloud Architecture</span>
        </div>

        <div className="flex items-center gap-6">
          <div className="flex items-center gap-1.5 hover:text-slate-300 transition-colors">
            <Database className="w-3.5 h-3.5 text-brand-400" />
            <span>TiDB Ready</span>
          </div>
          <div className="flex items-center gap-1.5 hover:text-slate-300 transition-colors">
            <GitBranch className="w-3.5 h-3.5 text-accent-400" />
            <span>NetworkX Graph Pipeline</span>
          </div>
          <div className="flex items-center gap-1.5 hover:text-slate-300 transition-colors">
            <Cpu className="w-3.5 h-3.5 text-emerald-400" />
            <span>LLM Grounding</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
