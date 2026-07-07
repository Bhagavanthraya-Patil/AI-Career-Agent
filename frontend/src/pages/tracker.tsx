import { motion } from "framer-motion";
import {
  GitCompareArrows,
  Send,
  TrendingUp,
  Award,
  Target,
} from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { EmptyState } from "@/components/shared/empty-state";

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

export default function Tracker() {
  const metrics = [
    {
      icon: <Send className="h-6 w-6" />,
      iconClassName: "bg-blue-500/10 text-blue-600",
      label: "Total Applications",
      value: 0,
    },
    {
      icon: <TrendingUp className="h-6 w-6" />,
      iconClassName: "bg-emerald-500/10 text-emerald-600",
      label: "Interviews",
      value: 0,
    },
    {
      icon: <Award className="h-6 w-6" />,
      iconClassName: "bg-amber-500/10 text-amber-600",
      label: "Offers",
      value: 0,
    },
    {
      icon: <Target className="h-6 w-6" />,
      iconClassName: "bg-purple-500/10 text-purple-600",
      label: "Success Rate",
      value: "0%",
    },
  ];

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-8"
    >
      <motion.div variants={itemVariants}>
        <PageHeader
          title="Tracker"
          description="Application status tracker"
        />
      </motion.div>

      <motion.div
        variants={itemVariants}
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        {metrics.map((metric) => (
          <StatCard key={metric.label} {...metric} />
        ))}
      </motion.div>

      <motion.div variants={itemVariants}>
        <EmptyState
          icon={
            <GitCompareArrows className="h-8 w-8 text-muted-foreground" />
          }
          title="No applications tracked"
          description="Start tracking your job applications to see your progress."
          action={{ label: "Track Applications", onClick: () => {} }}
        />
      </motion.div>
    </motion.div>
  );
}
