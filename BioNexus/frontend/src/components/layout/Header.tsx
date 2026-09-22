"use client";

import React, { useEffect, useState } from "react";
import { Dna, Activity, Sparkles, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { checkBackendHealth } from "@/lib/api";

export function Header() {
  const [healthStatus, setHealthStatus] = useState<string>("checking");

  useEffect(() => {
    async function verifyHealth() {
      try {
        const res = await checkBackendHealth();
        if (res.status === "ok") {
          setHealthStatus("online");
        } else {
          setHealthStatus("offline");
        }
      } catch {
        setHealthStatus("offline");
      }
    }
    verifyHealth();
    const interval = setInterval(verifyHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="border-b border-slate-800/80 bg-slate-950/70 backdrop-blur-xl sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
        {/* Brand Logo & Title */}
        <div className="flex items-center gap-4">
          <div className="relative flex items-center justify-center w-11 h-11 rounded-xl bg-gradient-to-br from-brand-400 via-brand-600 to-accent-600 p-[1px] shadow-lg shadow-brand-500/20">
            <div className="w-full h-full bg-slate-950 rounded-[11px] flex items-center justify-center">
              <Dna className="w-6 h-6 text-brand-400 animate-pulse-slow" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold font-heading tracking-tight bg-gradient-to-r from-white via-slate-100 to-brand-300 bg-clip-text text-transparent">
                BioNexus
              </span>
              <Badge variant="brand" className="text-[10px] py-0 px-2">
                v0.1.0 Early Access
              </Badge>
            </div>
            <p className="text-xs text-slate-400 hidden sm:block">
              Connecting Natural Compounds to Biological Insights
            </p>
          </div>
        </div>

        {/* Status Indicators & Meta */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 text-xs">
            <div
              className={`w-2 h-2 rounded-full ${
                healthStatus === "online"
                  ? "bg-emerald-400 shadow-sm shadow-emerald-400/80 animate-ping"
                  : healthStatus === "checking"
                  ? "bg-amber-400 animate-pulse"
                  : "bg-rose-500"
              }`}
            />
            <span className="text-slate-300 font-mono text-[11px]">
              API: {healthStatus === "online" ? "FastAPI Connected" : healthStatus}
            </span>
          </div>

          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden md:inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-brand-300 transition-colors px-3 py-1.5 rounded-lg hover:bg-slate-900 border border-transparent hover:border-slate-800"
          >
            <Activity className="w-3.5 h-3.5" />
            API Docs
          </a>
        </div>
      </div>
    </header>
  );
}
