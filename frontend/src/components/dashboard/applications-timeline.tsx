import { motion } from "framer-motion";
import {
  Send,
  Calendar,
  Gift,
  XCircle,
  ClipboardCheck,
  Bookmark,
  FileText,
  type LucideIcon,
} from "lucide-react";

import { cn, formatRelativeTime } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/dashboard/status-badge";
import { mockTimeline } from "@/data/dashboard";
import type { TimelineEvent } from "@/types";

interface ApplicationsTimelineProps {
  className?: string;
}

const typeIcon: Record<string, LucideIcon> = {
  application: Send,
  interview: Calendar,
  offer: Gift,
  rejection: XCircle,
  assessment: ClipboardCheck,
  saved: Bookmark,
  note: FileText,
};

const typeColor: Record<string, string> = {
  application: "bg-blue-500/10 text-blue-600 border-blue-200 dark:border-blue-800",
  interview: "bg-purple-500/10 text-purple-600 border-purple-200 dark:border-purple-800",
  offer: "bg-emerald-500/10 text-emerald-600 border-emerald-200 dark:border-emerald-800",
  rejection: "bg-red-500/10 text-red-600 border-red-200 dark:border-red-800",
  assessment: "bg-amber-500/10 text-amber-600 border-amber-200 dark:border-amber-800",
  saved: "bg-cyan-500/10 text-cyan-600 border-cyan-200 dark:border-cyan-800",
  note: "bg-slate-500/10 text-slate-600 border-slate-200 dark:border-slate-800",
};

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: { opacity: 1, x: 0 },
};

export function ApplicationsTimeline({ className }: ApplicationsTimelineProps) {
  return (
    <div className={cn("space-y-4", className)}>
      <div>
        <h2 className="text-lg font-semibold">Recent Activity</h2>
        <p className="text-sm text-muted-foreground">
          Your latest application events and updates
        </p>
      </div>

      <motion.div
        variants={containerVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true }}
        className="relative space-y-0"
      >
        <div className="absolute bottom-0 left-[19px] top-0 w-px bg-border md:left-1/2 md:-translate-x-px" />

        {mockTimeline.map((event, index) => (
          <TimelineItem
            key={event.id}
            event={event}
            index={index}
          />
        ))}
      </motion.div>
    </div>
  );
}

function TimelineItem({
  event,
  index,
}: {
  event: TimelineEvent;
  index: number;
}) {
  const Icon = typeIcon[event.type] ?? FileText;
  const isLeft = index % 2 === 0;

  return (
    <motion.div
      variants={itemVariants}
      className={cn(
        "relative flex items-start gap-4 pb-8 last:pb-0",
        "md:flex-row",
        isLeft ? "md:flex-row" : "md:flex-row-reverse",
      )}
    >
      <div
        className={cn(
          "relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 bg-background shadow-sm",
          typeColor[event.type] ?? "bg-muted text-muted-foreground",
        )}
      >
        <Icon className="h-4 w-4" />
      </div>

      <div
        className={cn(
          "flex-1",
          "md:w-[calc(50%-2rem)]",
          isLeft ? "md:text-right" : "md:text-left",
        )}
      >
        <Card className="border-border/50 shadow-sm">
          <CardContent className="p-4">
            <div
              className={cn(
                "flex flex-wrap items-start gap-2",
                isLeft ? "md:flex-row-reverse" : "md:flex-row",
              )}
            >
              <div className={cn("flex-1", isLeft ? "md:text-right" : "md:text-left")}>
                <h3 className="text-sm font-semibold">{event.title}</h3>
                {event.company && (
                  <p className="text-xs text-muted-foreground">{event.company}</p>
                )}
                <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                  {event.description}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <span className="text-[11px] text-muted-foreground">
                  {formatRelativeTime(event.timestamp)}
                </span>
                <StatusBadge status={event.status} showIcon={false} />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </motion.div>
  );
}
