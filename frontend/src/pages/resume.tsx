import { motion } from "framer-motion";
import { FileText, Upload } from "lucide-react";

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

export default function Resume() {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6"
    >
      <motion.div variants={itemVariants}>
        <PageHeader
          title="Resume"
          description="Manage your resumes and cover letters"
        />
      </motion.div>

      <motion.div variants={itemVariants}>
        <EmptyState
          icon={<FileText className="h-8 w-8 text-muted-foreground" />}
          title="No resumes uploaded"
          description="Upload your resume to get started with AI-powered analysis and tailoring."
          action={{ label: "Upload Resume", onClick: () => {} }}
        />
      </motion.div>
    </motion.div>
  );
}
