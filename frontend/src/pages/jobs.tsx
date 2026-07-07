import { motion } from "framer-motion";
import { Briefcase, Search } from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { Input } from "@/components/ui/input";

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

export default function Jobs() {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6"
    >
      <motion.div variants={itemVariants}>
        <PageHeader
          title="Jobs"
          description="Track and manage job listings"
        />
      </motion.div>

      <motion.div variants={itemVariants} className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input placeholder="Search jobs..." className="pl-9" />
      </motion.div>

      <motion.div variants={itemVariants}>
        <EmptyState
          icon={<Briefcase className="h-8 w-8 text-muted-foreground" />}
          title="No jobs yet"
          description="Start searching for jobs to build your list."
          action={{ label: "Search Jobs", onClick: () => {} }}
        />
      </motion.div>
    </motion.div>
  );
}
