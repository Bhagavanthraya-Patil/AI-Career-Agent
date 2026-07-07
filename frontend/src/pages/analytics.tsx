import { motion } from "framer-motion";
import {
  BarChart3,
  Briefcase,
  TrendingUp,
  Award,
  Target,
  Clock,
} from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

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

export default function Analytics() {
  const stats = [
    {
      icon: <Briefcase className="h-6 w-6" />,
      iconClassName: "bg-blue-500/10 text-blue-600",
      label: "Total Applications",
      value: 0,
    },
    {
      icon: <TrendingUp className="h-6 w-6" />,
      iconClassName: "bg-emerald-500/10 text-emerald-600",
      label: "Interview Rate",
      value: "0%",
    },
    {
      icon: <Award className="h-6 w-6" />,
      iconClassName: "bg-amber-500/10 text-amber-600",
      label: "Offer Rate",
      value: "0%",
    },
    {
      icon: <Target className="h-6 w-6" />,
      iconClassName: "bg-purple-500/10 text-purple-600",
      label: "Response Rate",
      value: "0%",
    },
  ];

  const chartPlaceholders = [
    { title: "Applications Over Time", color: "bg-primary/10" },
    { title: "Status Distribution", color: "bg-emerald-500/10" },
    { title: "Source Breakdown", color: "bg-amber-500/10" },
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
          title="Analytics"
          description="Job search insights and metrics"
        />
      </motion.div>

      <motion.div
        variants={itemVariants}
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        {stats.map((stat) => (
          <StatCard key={stat.label} {...stat} />
        ))}
      </motion.div>

      <motion.div
        variants={itemVariants}
        className="grid gap-6 md:grid-cols-2 lg:grid-cols-3"
      >
        {chartPlaceholders.map((chart) => (
          <Card key={chart.title}>
            <CardHeader>
              <CardTitle className="text-sm font-medium">
                {chart.title}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div
                className={`flex h-48 items-center justify-center rounded-lg ${chart.color}`}
              >
                <div className="text-center">
                  <BarChart3 className="mx-auto h-8 w-8 text-muted-foreground/50" />
                  <p className="mt-2 text-xs text-muted-foreground">
                    Chart coming soon
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </motion.div>
    </motion.div>
  );
}
