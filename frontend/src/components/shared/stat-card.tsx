import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { TrendingUp, TrendingDown } from "lucide-react";

import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";

interface StatCardProps {
  icon: ReactNode;
  iconClassName?: string;
  label: string;
  value: string | number;
  trend?: {
    value: number;
    isUp: boolean;
  };
  className?: string;
}

export function StatCard({
  icon,
  iconClassName,
  label,
  value,
  trend,
  className,
}: StatCardProps) {
  return (
    <motion.div
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      className={cn("", className)}
    >
      <Card className="h-full border border-border/50 shadow-sm backdrop-blur-sm bg-card/90">
        <CardContent className="p-6">
          <div className="flex items-start justify-between">
            <div
              className={cn(
                "flex h-12 w-12 items-center justify-center rounded-xl",
                iconClassName ?? "bg-primary/10 text-primary",
              )}
            >
              {icon}
            </div>
            {trend && (
              <div
                className={cn(
                  "flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
                  trend.isUp
                    ? "bg-success/10 text-success"
                    : "bg-destructive/10 text-destructive",
                )}
              >
                {trend.isUp ? (
                  <TrendingUp className="h-3 w-3" />
                ) : (
                  <TrendingDown className="h-3 w-3" />
                )}
                {Math.abs(trend.value)}%
              </div>
            )}
          </div>
          <div className="mt-4">
            <p className="text-sm text-muted-foreground">{label}</p>
            <p className="mt-1 text-2xl font-semibold tracking-tight">
              {value}
            </p>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
