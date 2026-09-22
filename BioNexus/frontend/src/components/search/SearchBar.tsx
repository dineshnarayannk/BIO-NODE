"use client";

import React, { useState } from "react";
import { Search, Sparkles, Loader2, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

interface SearchBarProps {
  onSearch: (query: string) => void;
  isLoading?: boolean;
}

const SAMPLE_COMPOUNDS = [
  { name: "Curcumin", class: "Polyphenol" },
  { name: "Resveratrol", class: "Stilbenoid" },
  { name: "Capreomycin", class: "Streptomyces Peptide" },
  { name: "Quercetin", class: "Flavonoid" },
  { name: "Actinomycin D", class: "Chromopeptide" },
];

export function SearchBar({ onSearch, isLoading = false }: SearchBarProps) {
  const [query, setQuery] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
    }
  };

  const handleSelectSample = (name: string) => {
    setQuery(name);
    onSearch(name);
  };

  return (
    <div className="w-full max-w-3xl mx-auto space-y-4">
      <form onSubmit={handleSubmit} className="relative flex items-center shadow-2xl">
        <div className="absolute left-4.5 text-slate-400 pointer-events-none flex items-center">
          <Search className="w-5 h-5 text-brand-400" />
        </div>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter a natural compound..."
          className="w-full pl-12 pr-32 py-4 rounded-2xl bg-slate-900/90 border border-slate-700/70 text-white placeholder-slate-500 text-base md:text-lg focus:outline-none focus:ring-2 focus:ring-brand-400/50 focus:border-brand-500 backdrop-blur-xl transition-all shadow-inner"
        />
        <div className="absolute right-2 flex items-center gap-2">
          <Button
            type="submit"
            disabled={!query.trim() || isLoading}
            className="rounded-xl px-5 py-2.5 shadow-md shadow-brand-500/25"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin mr-1.5" />
                Searching...
              </>
            ) : (
              <>
                Analyze
                <ArrowRight className="w-4 h-4 ml-1" />
              </>
            )}
          </Button>
        </div>
      </form>

      {/* Suggested Quick Select Tokens */}
      <div className="flex flex-wrap items-center justify-center gap-2 pt-2 text-xs">
        <span className="text-slate-400 flex items-center gap-1">
          <Sparkles className="w-3.5 h-3.5 text-brand-400" /> Suggestions:
        </span>
        {SAMPLE_COMPOUNDS.map((c) => (
          <button
            key={c.name}
            type="button"
            onClick={() => handleSelectSample(c.name)}
            className="px-2.5 py-1 rounded-lg bg-slate-900/60 border border-slate-800 text-slate-300 hover:text-white hover:border-brand-500/40 hover:bg-brand-500/10 transition-all cursor-pointer flex items-center gap-1.5"
          >
            <span>{c.name}</span>
            <span className="text-[10px] text-slate-400 font-mono">({c.class})</span>
          </button>
        ))}
      </div>
    </div>
  );
}
