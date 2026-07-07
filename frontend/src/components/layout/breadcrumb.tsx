import { Link } from "react-router-dom";
import { ChevronRight, Home } from "lucide-react";
import { motion } from "framer-motion";

import { cn } from "@/lib/utils";

export interface BreadcrumbSegment {
  label: string;
  href?: string;
}

interface BreadcrumbProps {
  segments: BreadcrumbSegment[];
  className?: string;
}

const stagger = {
  animate: {
    transition: {
      staggerChildren: 0.05,
    },
  },
};

const fadeIn = {
  initial: { opacity: 0, x: -8 },
  animate: { opacity: 1, x: 0 },
};

export function Breadcrumb({ segments, className }: BreadcrumbProps) {
  return (
    <motion.nav
      variants={stagger}
      initial="initial"
      animate="animate"
      className={cn("flex items-center gap-1.5 text-sm text-muted-foreground", className)}
    >
      <motion.div key="home" variants={fadeIn}>
        <Link
          to="/dashboard"
          className="flex items-center gap-1 transition-colors hover:text-foreground"
        >
          <Home className="h-4 w-4" />
        </Link>
      </motion.div>

      {segments.map((segment, index) => (
        <motion.div
          key={`${segment.label}-${index}`}
          variants={fadeIn}
          className="flex items-center gap-1.5"
        >
          <ChevronRight className="h-4 w-4" />
          {segment.href ? (
            <Link
              to={segment.href}
              className="transition-colors hover:text-foreground"
            >
              {segment.label}
            </Link>
          ) : (
            <span className="text-foreground font-medium">
              {segment.label}
            </span>
          )}
        </motion.div>
      ))}
    </motion.nav>
  );
}
