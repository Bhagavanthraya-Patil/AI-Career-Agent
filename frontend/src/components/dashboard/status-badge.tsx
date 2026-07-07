import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { ApplicationStatus } from "@/types";
import {
  FileText,
  CheckCircle2,
  Send,
  Upload,
  Eye,
  ClipboardCheck,
  Calendar,
  Laptop,
  Users,
  Gift,
  CheckCircle,
  XCircle,
  LogOut,
  Clock,
  AlertTriangle,
  Ban,
  type LucideIcon,
} from "lucide-react";

interface StatusBadgeProps {
  status: ApplicationStatus;
  showIcon?: boolean;
  className?: string;
}

const statusConfig: Record<
  ApplicationStatus,
  {
    variant: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info";
    icon: LucideIcon;
    label: string;
  }
> = {
  draft: { variant: "secondary", icon: FileText, label: "Draft" },
  ready: { variant: "default", icon: CheckCircle2, label: "Ready" },
  applied: { variant: "info", icon: Send, label: "Applied" },
  submitted: { variant: "info", icon: Upload, label: "Submitted" },
  viewed: { variant: "default", icon: Eye, label: "Viewed" },
  assessment: { variant: "warning", icon: ClipboardCheck, label: "Assessment" },
  interview: { variant: "info", icon: Calendar, label: "Interview" },
  technical_interview: { variant: "info", icon: Laptop, label: "Tech Interview" },
  hr_interview: { variant: "info", icon: Users, label: "HR Interview" },
  offer: { variant: "success", icon: Gift, label: "Offer" },
  accepted: { variant: "success", icon: CheckCircle, label: "Accepted" },
  rejected: { variant: "destructive", icon: XCircle, label: "Rejected" },
  withdrawn: { variant: "secondary", icon: LogOut, label: "Withdrawn" },
  expired: { variant: "outline", icon: Clock, label: "Expired" },
  failed: { variant: "destructive", icon: AlertTriangle, label: "Failed" },
  cancelled: { variant: "outline", icon: Ban, label: "Cancelled" },
};

export function StatusBadge({ status, showIcon = true, className }: StatusBadgeProps) {
  const config = statusConfig[status] ?? statusConfig.draft;
  const Icon = config.icon;

  return (
    <Badge variant={config.variant} className={cn("gap-1", className)}>
      {showIcon && <Icon className="h-3 w-3" />}
      {config.label}
    </Badge>
  );
}

export { statusConfig };
