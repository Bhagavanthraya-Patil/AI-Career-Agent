import { motion } from "framer-motion";
import { ScrollText } from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
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

export default function AtsAnalyzer() {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6"
    >
      <motion.div variants={itemVariants}>
        <PageHeader
          title="ATS Analyzer"
          description="Check your resume against job descriptions"
        />
      </motion.div>

      <motion.div variants={itemVariants}>
        <EmptyState
          icon={<ScrollText className="h-8 w-8 text-muted-foreground" />}
          title="No analysis yet"
          description="Submit a job description and your resume to see how well they match."
          action={{ label: "Analyze Resume", onClick: () => {} }}
        />
      </motion.div>
    </motion.div>
  );
}
