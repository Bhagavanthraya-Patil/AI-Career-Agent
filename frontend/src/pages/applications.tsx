import { motion } from "framer-motion";
import { Send } from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

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

const tabs = [
  { value: "all", label: "All" },
  { value: "applied", label: "Applied" },
  { value: "interviewing", label: "Interviewing" },
  { value: "offers", label: "Offers" },
  { value: "rejected", label: "Rejected" },
];

export default function Applications() {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6"
    >
      <motion.div variants={itemVariants}>
        <PageHeader
          title="Applications"
          description="Track your job applications"
        />
      </motion.div>

      <motion.div variants={itemVariants}>
        <Tabs defaultValue="all">
          <TabsList>
            {tabs.map((tab) => (
              <TabsTrigger key={tab.value} value={tab.value}>
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>
          {tabs.map((tab) => (
            <TabsContent key={tab.value} value={tab.value}>
              <EmptyState
                icon={<Send className="h-8 w-8 text-muted-foreground" />}
                title={`No ${tab.label.toLowerCase()} applications`}
                description={
                  tab.value === "all"
                    ? "Start applying to jobs to see your applications here."
                    : `No applications with "${tab.label.toLowerCase()}" status.`
                }
              />
            </TabsContent>
          ))}
        </Tabs>
      </motion.div>
    </motion.div>
  );
}
