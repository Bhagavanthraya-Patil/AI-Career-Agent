import { motion } from "framer-motion";
import {
  Briefcase,
  Send,
  Bookmark,
  CalendarCheck,
  Gift,
  XCircle,
  FileText,
  Target,
  TrendingUp,
  TrendingDown,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { formatNumber } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { AnimatedCounter } from "@/components/dashboard/animated-counter";
import { mockStats, mockTrends } from "@/data/dashboard";

interface StatsCardsProps {
  className?: string;
}

const statCards = [
  {
    label: "Total Jobs",
    key: "totalJobs" as const,
    icon: <Briefcase className="h-5 w-5" />,
    iconBg: "bg-blue-500/10 text-blue-600",
  },
  {
    label: "Applied",
    key: "appliedJobs" as const,
    icon: <Send className="h-5 w-5" />,
    iconBg: "bg-emerald-500/10 text-emerald-600",
  },
  {
    label: "Saved",
    key: "savedJobs" as const,
    icon: <Bookmark className="h-5 w-5" />,
    iconBg: "bg-amber-500/10 text-amber-600",
  },
  {
    label: "Interviews",
    key: "interviews" as const,
    icon: <CalendarCheck className="h-5 w-5" />,
    iconBg: "bg-purple-500/10 text-purple-600",
  },
  {
    label: "Offers",
    key: "offers" as const,
    icon: <Gift className="h-5 w-5" />,
    iconBg: "bg-rose-500/10 text-rose-600",
  },
  {
    label: "Rejections",
    key: "rejections" as const,
    icon: <XCircle className="h-5 w-5" />,
    iconBg: "bg-red-500/10 text-red-600",
  },
  {
    label: "Resume Score",
    key: "resumeScore" as const,
    icon: <FileText className="h-5 w-5" />,
    iconBg: "bg-cyan-500/10 text-cyan-600",
  },
  {
    label: "ATS Score",
    key: "atsScore" as const,
    icon: <Target className="h-5 w-5" />,
    iconBg: "bg-orange-500/10 text-orange-600",
  },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.06 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

export function StatsCards({ className }: StatsCardsProps) {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true }}
      className={cn(
        "grid gap-4 sm:grid-cols-2 lg:grid-cols-4",
        className,
      )}
    >
      {statCards.map((stat) => {
        const value = mockStats[stat.key];
        const trend = mockTrends[stat.key];
        const trendIndicator = trend
          ? { value: Math.abs(trend), isUp: trend >= 0 }
          : undefined;

        return (
          <motion.div key={stat.key} variants={itemVariants}>
            <Card className="h-full border border-border/50 shadow-sm backdrop-blur-sm">
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div
                    className={cn(
                      "flex h-12 w-12 items-center justify-center rounded-xl",
                      stat.iconBg,
                    )}
                  >
                    {stat.icon}
                  </div>
                  {trendIndicator && (
                    <div
                      className={cn(
                        "flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
                        trendIndicator.isUp
                          ? "bg-success/10 text-success"
                          : "bg-destructive/10 text-destructive",
                      )}
                    >
                      {trendIndicator.isUp ? (
                        <TrendingUp className="h-3 w-3" />
                      ) : (
                        <TrendingDown className="h-3 w-3" />
                      )}
                      {trendIndicator.value}%
                    </div>
                  )}
                </div>
                <div className="mt-4">
                  <p className="text-sm text-muted-foreground">{stat.label}</p>
                  <p className="mt-1 text-2xl font-semibold tracking-tight">
                    <AnimatedCounter
                      value={value}
                      suffix={
                        stat.key === "resumeScore" || stat.key === "atsScore"
                          ? "%"
                          : ""
                      }
                    />
                  </p>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        );
      })}
    </motion.div>
  );
}

