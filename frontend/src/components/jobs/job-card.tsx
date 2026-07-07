import { useState } from "react";
import { motion } from "framer-motion";
import {
  MapPin,
  DollarSign,
  Clock,
  Bookmark,
  BookmarkCheck,
  Building2,
} from "lucide-react";

import { cn, formatRelativeTime } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Job } from "@/types";

interface JobCardProps {
  job: Job;
  isSelected: boolean;
  onSelect: (id: string) => void;
}

function formatSalary(min?: number, max?: number, currency?: string): string {
  if (!min && !max) return "Not specified";
  const fmt = (n: number) => {
    if (n >= 1000) return `$${(n / 1000).toFixed(0)}k`;
    return `$${n.toLocaleString()}`;
  };
  if (min && max) return `${fmt(min)} - ${fmt(max)}`;
  if (min) return `From ${fmt(min)}`;
  return `Up to ${fmt(max!)}`;
}

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

const statusBadgeVariant: Record<string, "success" | "secondary" | "default" | "destructive" | "outline" | "warning" | "info"> = {
  active: "success",
  closed: "secondary",
  draft: "warning",
  archived: "outline",
};

function getStatusVariant(status: string) {
  return statusBadgeVariant[status] ?? "secondary";
}

const employmentColors: Record<string, string> = {
  full_time: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  part_time: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  contract: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  internship: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  freelance: "bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400",
  temporary: "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400",
};

function getEmploymentStyles(type: string): string {
  return employmentColors[type] ?? "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400";
}

export function JobCard({ job, isSelected, onSelect }: JobCardProps) {
  const [isBookmarked, setIsBookmarked] = useState(false);

  const companyInitial = job.company.name.charAt(0).toUpperCase();

  const colors = [
    "bg-blue-500", "bg-emerald-500", "bg-violet-500", "bg-amber-500",
    "bg-rose-500", "bg-cyan-500", "bg-pink-500", "bg-indigo-500",
  ];
  const colorIndex = job.company.name.length % colors.length;
  const avatarColor = colors[colorIndex];

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -1 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
    >
      <Card
        className={cn(
          "group cursor-pointer border-border/50 transition-shadow duration-200 hover:shadow-md",
          isSelected && "border-l-2 border-l-primary shadow-sm",
        )}
        onClick={() => onSelect(job.id)}
      >
        <CardContent className="p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
            <div className="flex items-center gap-3 sm:min-w-0 sm:flex-1">
              {job.company.logo_url ? (
                <img
                  src={job.company.logo_url}
                  alt={job.company.name}
                  className="h-10 w-10 flex-shrink-0 rounded-lg object-cover"
                />
              ) : (
                <div
                  className={cn(
                    "flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg text-sm font-bold text-white",
                    avatarColor,
                  )}
                >
                  {companyInitial}
                </div>
              )}
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-muted-foreground">
                  {job.company.name}
                </p>
                <p className="truncate text-base font-semibold leading-tight">
                  {job.title}
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground sm:flex-shrink-0 sm:gap-4">
              {job.location && (
                <span className="inline-flex items-center gap-1">
                  <MapPin className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate max-w-[120px]">{job.location}</span>
                </span>
              )}

              {(job.salary_min || job.salary_max) && (
                <span className="inline-flex items-center gap-1 font-medium text-emerald-600 dark:text-emerald-400">
                  <DollarSign className="h-3.5 w-3.5 shrink-0" />
                  {formatSalary(job.salary_min, job.salary_max, job.currency)}
                </span>
              )}

              {job.employment_type && (
                <span
                  className={cn(
                    "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium",
                    getEmploymentStyles(job.employment_type),
                  )}
                >
                  {job.employment_type.replace("_", " ")}
                </span>
              )}
            </div>

            <div className="flex items-center gap-2 sm:flex-shrink-0">
              <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                <Clock className="h-3.5 w-3.5 shrink-0" />
                {formatRelativeTime(job.created_at)}
              </span>

              {job.source?.name && (
                <Badge variant="outline" className="hidden text-[10px] sm:inline-flex">
                  {job.source.name}
                </Badge>
              )}

              <Badge
                variant={getStatusVariant(job.status)}
                className="hidden text-[10px] capitalize sm:inline-flex"
              >
                {job.status}
              </Badge>

              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 shrink-0"
                onClick={(e) => {
                  e.stopPropagation();
                  setIsBookmarked((prev) => !prev);
                }}
              >
                {isBookmarked ? (
                  <BookmarkCheck className="h-4 w-4 text-primary" />
                ) : (
                  <Bookmark className="h-4 w-4 text-muted-foreground" />
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
