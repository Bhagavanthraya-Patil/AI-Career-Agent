import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import {
  Send,
  ScrollText,
  Wand2,
  Upload,
  RefreshCw,
  GitCompareArrows,
  type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { mockQuickActions } from "@/data/dashboard";

interface QuickActionsProps {
  className?: string;
}

const iconMap: Record<string, LucideIcon> = {
  Send,
  ScrollText,
  Wand2,
  Upload,
  RefreshCw,
  GitCompareArrows,
};

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

export function QuickActions({ className }: QuickActionsProps) {
  return (
    <div className={cn("space-y-4", className)}>
      <div>
        <h2 className="text-lg font-semibold">Quick Actions</h2>
        <p className="text-sm text-muted-foreground">
          Frequently used tools and shortcuts
        </p>
      </div>

      <motion.div
        variants={containerVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true }}
        className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3"
      >
        {mockQuickActions.map((action) => {
          const Icon = iconMap[action.icon];
          if (!Icon) return null;

          return (
            <motion.div key={action.id} variants={itemVariants}>
              <Link to={action.href} className="block">
                <Card className="cursor-pointer border-border/50 shadow-sm transition-colors hover:border-border">
                  <CardContent className="flex items-start gap-3 p-4">
                    <div
                      className={cn(
                        "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
                        action.color,
                      )}
                    >
                      <Icon className="h-5 w-5" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">{action.label}</p>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {action.description}
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            </motion.div>
          );
        })}
      </motion.div>
    </div>
  );
}
