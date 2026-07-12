"use client";

import { motion } from "framer-motion";
import { BudgetBreakdown as BudgetBreakdownType, formatINR } from "@/lib/api";

interface BudgetBreakdownProps {
  budget: BudgetBreakdownType;
  totalBudget: number;
}

const CATEGORIES = [
  { key: "transport" as const, label: "Transport", color: "#8b5cf6", icon: "🚀" },
  { key: "food" as const, label: "Food & Dining", color: "#f59e0b", icon: "🍛" },
  { key: "activities" as const, label: "Activities", color: "#06b6d4", icon: "🎯" },
  { key: "accommodation" as const, label: "Accommodation", color: "#22c55e", icon: "🏨" },
  { key: "miscellaneous" as const, label: "Miscellaneous", color: "#ec4899", icon: "📦" },
];

export default function BudgetBreakdownComponent({
  budget,
  totalBudget,
}: BudgetBreakdownProps) {
  const usedPercent = Math.min(
    (budget.total_estimated / totalBudget) * 100,
    100
  );
  const isOverBudget = budget.total_estimated > totalBudget;

  return (
    <div className="glass p-5 rounded-xl space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-bold font-[family-name:var(--font-outfit)] text-foreground">
          💰 Budget Breakdown
        </h3>
        <div className="text-right">
          <div className="text-sm text-foreground-muted">
            {formatINR(budget.total_estimated)} / {formatINR(totalBudget)}
          </div>
        </div>
      </div>

      {/* Progress Ring (simplified as bar) */}
      <div className="relative w-full h-3 bg-glass-bg rounded-full overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${
            isOverBudget
              ? "bg-gradient-to-r from-error to-error/70"
              : "bg-gradient-to-r from-primary to-accent"
          }`}
          initial={{ width: 0 }}
          animate={{ width: `${usedPercent}%` }}
          transition={{ duration: 1, ease: "easeOut", delay: 0.3 }}
        />
      </div>

      <div className="flex justify-between text-xs">
        <span className={isOverBudget ? "text-error font-medium" : "text-foreground-muted"}>
          {usedPercent.toFixed(0)}% used
        </span>
        <span
          className={`font-medium ${
            isOverBudget ? "text-error" : "text-success"
          }`}
        >
          {isOverBudget ? "Over budget!" : `${formatINR(budget.remaining)} remaining`}
        </span>
      </div>

      {/* Category bars */}
      <div className="space-y-3">
        {CATEGORIES.map((cat) => {
          const amount = budget[cat.key];
          const percent =
            budget.total_estimated > 0
              ? (amount / budget.total_estimated) * 100
              : 0;

          if (amount === 0) return null;

          return (
            <div key={cat.key} className="flex items-center gap-3">
              <span className="text-lg w-7 text-center">{cat.icon}</span>
              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm text-foreground">{cat.label}</span>
                  <span className="text-sm font-medium text-foreground">
                    {formatINR(amount)}
                  </span>
                </div>
                <div className="w-full h-1.5 bg-glass-bg rounded-full overflow-hidden">
                  <motion.div
                    className="h-full rounded-full"
                    style={{ backgroundColor: cat.color }}
                    initial={{ width: 0 }}
                    animate={{ width: `${percent}%` }}
                    transition={{ duration: 0.8, ease: "easeOut", delay: 0.5 }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
