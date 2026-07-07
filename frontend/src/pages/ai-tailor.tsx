import { motion } from "framer-motion";
import { Wand2 } from "lucide-react";

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

export default function AiTailor() {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6"
    >
      <motion.div variants={itemVariants}>
        <PageHeader
          title="AI Tailor"
          description="Tailor your resume for specific roles"
        />
      </motion.div>

      <motion.div variants={itemVariants}>
        <EmptyState
          icon={<Wand2 className="h-8 w-8 text-muted-foreground" />}
          title="No tailoring sessions"
          description="Start a new session to optimize your resume for a specific job."
          action={{ label: "New Session", onClick: () => {} }}
        />
      </motion.div>
    </motion.div>
  );
}
