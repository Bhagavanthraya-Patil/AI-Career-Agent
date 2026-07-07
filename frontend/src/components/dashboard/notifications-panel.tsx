import { useState } from "react";
import { motion } from "framer-motion";
import { Bell, Sparkles, Info, CheckCheck, type LucideIcon } from "lucide-react";

import { cn, formatRelativeTime } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { mockNotifications } from "@/data/dashboard";
import type { DashboardNotification } from "@/types";

interface NotificationsPanelProps {
  className?: string;
}

const typeIcon: Record<string, LucideIcon> = {
  activity: Bell,
  recommendation: Sparkles,
  system: Info,
};

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.06 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, x: -10 },
  visible: { opacity: 1, x: 0 },
};

export function NotificationsPanel({ className }: NotificationsPanelProps) {
  const [notifications, setNotifications] = useState(mockNotifications);
  const unreadCount = notifications.filter((n) => !n.read).length;

  function markAllRead() {
    setNotifications((prev) =>
      prev.map((n) => ({ ...n, read: true })),
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      <Card className="border-border/50 shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div className="flex items-center gap-2">
            <CardTitle className="text-lg font-semibold">Notifications</CardTitle>
            {unreadCount > 0 && (
              <Badge variant="default" className="h-5 px-1.5 text-[10px]">
                {unreadCount}
              </Badge>
            )}
          </div>
          {unreadCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1 text-xs text-muted-foreground"
              onClick={markAllRead}
            >
              <CheckCheck className="h-3.5 w-3.5" />
              Mark all read
            </Button>
          )}
        </CardHeader>
        <CardContent className="p-0">
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
          >
            {notifications.map((notification) => (
              <NotificationItem
                key={notification.id}
                notification={notification}
              />
            ))}
          </motion.div>
        </CardContent>
      </Card>
    </div>
  );
}

function NotificationItem({
  notification,
}: {
  notification: DashboardNotification;
}) {
  const Icon = typeIcon[notification.type] ?? Bell;

  return (
    <motion.div
      variants={itemVariants}
      className={cn(
        "relative border-b border-border/50 px-5 py-3.5 transition-colors last:border-b-0 hover:bg-muted/30",
        !notification.read && "border-l-2 border-l-primary",
      )}
    >
      <div className="flex items-start gap-3">
        <div
          className={cn(
            "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
            notification.type === "activity"
              ? "bg-blue-500/10 text-blue-600"
              : notification.type === "recommendation"
                ? "bg-amber-500/10 text-amber-600"
                : "bg-slate-500/10 text-slate-600",
          )}
        >
          <Icon className="h-4 w-4" />
        </div>
        <div className="flex-1 space-y-0.5">
          <div className="flex items-center gap-2">
            <p
              className={cn(
                "text-sm",
                !notification.read ? "font-semibold" : "font-medium",
              )}
            >
              {notification.title}
            </p>
            {!notification.read && (
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            {notification.message}
          </p>
          <p className="text-[11px] text-muted-foreground/60">
            {formatRelativeTime(notification.timestamp)}
          </p>
        </div>
      </div>
    </motion.div>
  );
}
