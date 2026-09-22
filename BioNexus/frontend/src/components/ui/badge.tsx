import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "brand" | "accent" | "slate" | "warning";
}

export function Badge({
  className,
  variant = "brand",
  ...props
}: BadgeProps) {
  const variantStyles = {
    brand: "bg-brand-500/10 text-brand-300 border-brand-500/30",
    accent: "bg-accent-500/10 text-accent-300 border-accent-500/30",
    slate: "bg-slate-800/80 text-slate-300 border-slate-700/60",
    warning: "bg-amber-500/10 text-amber-300 border-amber-500/30",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border tracking-wide",
        variantStyles[variant],
        className
      )}
      {...props}
    />
  );
}
