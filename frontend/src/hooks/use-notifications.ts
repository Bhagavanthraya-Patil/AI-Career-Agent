import { useEffect, useCallback, useRef } from "react";
import { useNotificationStore } from "@/store/notification-store";
import type { Notification } from "@/store/notification-store";

export function useNotifications(dismissAfter = 5000) {
  const {
    notifications,
    unreadCount,
    addNotification,
    markAsRead,
    markAllAsRead,
    clearNotifications,
  } = useNotificationStore();

  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  useEffect(() => {
    if (notifications.length === 0) return;
    const latest = notifications[0];
    if (timersRef.current.has(latest.id)) return;
    const timer = setTimeout(() => {
      markAsRead(latest.id);
      timersRef.current.delete(latest.id);
    }, dismissAfter);
    timersRef.current.set(latest.id, timer);
    return () => {
      clearTimeout(timer);
      timersRef.current.delete(latest.id);
    };
  }, [notifications, dismissAfter, markAsRead]);

  const notify = useCallback(
    (notification: Omit<Notification, "id" | "createdAt" | "read">) =>
      addNotification({
        id: crypto.randomUUID(),
        createdAt: new Date().toISOString(),
        read: false,
        ...notification,
      }),
    [addNotification],
  );

  return {
    notifications,
    unreadCount,
    notify,
    dismissNotification: markAsRead,
    clearAll: clearNotifications,
    markAllRead: markAllAsRead,
  };
}
