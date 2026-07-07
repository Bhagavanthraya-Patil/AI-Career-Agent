import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";

import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { mockInsights } from "@/data/dashboard";
import type { InsightCard } from "@/types";

interface AiInsightsProps {
  className?: string;
}

const priorityBorder: Record<string, string> = {
  high: "border-l-destructive",
  medium: "border-l-warning",
  low: "border-l-info",
};

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

function CircularScore({ score, size = 56 }: { score: number; size?: number }) {
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - score / 100);
  const strokeWidth = 4;

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="hsl(var(--muted))"
          strokeWidth={strokeWidth}
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          whileInView={{ strokeDashoffset: offset }}
          viewport={{ once: true }}
          transition={{ duration: 1.2, ease: "easeOut" }}
          className={cn(
            score >= 80
              ? "text-success"
              : score >= 60
                ? "text-warning"
                : "text-destructive",
          )}
        />
      </svg>
      <span className="absolute text-xs font-semibold tabular-nums">
        {score}%
      </span>
    </div>
  );
}

export function AiInsights({ className }: AiInsightsProps) {
  return (
    <div className={cn("space-y-4", className)}>
      <div>
        <h2 className="text-lg font-semibold">AI Insights</h2>
        <p className="text-sm text-muted-foreground">
          Smart recommendations based on your profile and market data
        </p>
      </div>

      <motion.div
        variants={containerVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true }}
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
      >
        {mockInsights.map((insight) => (
          <InsightCard
            key={insight.id}
            insight={insight}
          />
        ))}
      </motion.div>
    </div>
  );
}

function InsightCard({ insight }: { insight: InsightCard }) {
  return (
    <motion.div variants={itemVariants}>
      <Card
        className={cn(
          "h-full border-l-4 border-border/50 shadow-sm",
          priorityBorder[insight.priority] ?? "border-l-border",
        )}
      >
        <CardContent className="p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 space-y-1.5">
              <h3 className="text-sm font-semibold leading-tight">
                {insight.title}
              </h3>
              <p className="text-xs leading-relaxed text-muted-foreground">
                {insight.description}
              </p>
            </div>
            {insight.score !== undefined && (
              <CircularScore score={insight.score} />
            )}
          </div>
          {insight.action && (
            <Button
              variant="ghost"
              size="sm"
              className="mt-3 h-7 gap-1 px-2 text-xs font-medium text-primary"
            >
              {insight.action}
              <ArrowRight className="h-3 w-3" />
            </Button>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
