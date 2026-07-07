import { motion } from "framer-motion";

import { WelcomeHeader } from "@/components/dashboard/welcome-header";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { JobsTable } from "@/components/dashboard/jobs-table";
import { AiInsights } from "@/components/dashboard/ai-insights";
import { ApplicationsTimeline } from "@/components/dashboard/applications-timeline";
import { QuickActions } from "@/components/dashboard/quick-actions";
import { MarketOverview } from "@/components/dashboard/market-overview";
import { NotificationsPanel } from "@/components/dashboard/notifications-panel";

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.06 },
  },
};

const sectionVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.1, 0.25, 1] as const } },
};

export default function Dashboard() {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-8 pb-8"
    >
      <motion.div variants={sectionVariants}>
        <WelcomeHeader />
      </motion.div>

      <motion.div variants={sectionVariants}>
        <StatsCards />
      </motion.div>

      <motion.div variants={sectionVariants}>
        <AiInsights />
      </motion.div>

      <div className="grid gap-6 lg:grid-cols-3">
        <motion.div
          variants={sectionVariants}
          className="lg:col-span-2"
        >
          <JobsTable />
        </motion.div>
        <motion.div variants={sectionVariants}>
          <QuickActions />
        </motion.div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <motion.div
          variants={sectionVariants}
          className="lg:col-span-2"
        >
          <ApplicationsTimeline />
        </motion.div>
        <motion.div variants={sectionVariants}>
          <NotificationsPanel />
        </motion.div>
      </div>

      <motion.div variants={sectionVariants}>
        <MarketOverview />
      </motion.div>
    </motion.div>
  );
}
