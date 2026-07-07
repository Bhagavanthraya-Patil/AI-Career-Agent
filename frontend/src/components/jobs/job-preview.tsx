import { motion, AnimatePresence } from "framer-motion";
import {
  X, MapPin, Briefcase, DollarSign, Calendar, Clock,
  ExternalLink, Bookmark, Wifi, Layers,
  Building2, FileText, Sparkles
} from "lucide-react";
import { cn, formatDate } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { useJob } from "@/hooks/use-jobs";
import type { Job } from "@/types";

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
  return name.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2);
}

const avatarColors = [
  "bg-blue-500", "bg-emerald-500", "bg-violet-500", "bg-amber-500",
  "bg-rose-500", "bg-cyan-500", "bg-pink-500", "bg-indigo-500",
];

function getAvatarColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return avatarColors[Math.abs(hash) % avatarColors.length];
}

const statusVariantMap: Record<string, "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info"> = {
  active: "success",
  saved: "info",
  applied: "info",
  interviewing: "warning",
  offered: "success",
  rejected: "destructive",
  expired: "outline",
  closed: "secondary",
};

function getStatusVariant(status: string) {
  return statusVariantMap[status.toLowerCase()] ?? "secondary";
}

interface JobPreviewProps {
  jobId: string | null;
  onClose: () => void;
}

function JobPreviewContent({ job, onClose }: { job: Job; onClose: () => void }) {
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <div
            className={cn(
              "flex h-14 w-14 items-center justify-center rounded-xl text-lg font-bold text-white",
              getAvatarColor(job.company.name)
            )}
          >
            {getInitials(job.company.name)}
          </div>
          <div>
            <p className="text-lg font-semibold">{job.company.name}</p>
            <h2 className="text-2xl font-bold tracking-tight">{job.title}</h2>
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close panel">
          <X className="h-5 w-5" />
        </Button>
      </div>

      <div className="flex flex-wrap gap-2">
        {job.location && (
          <Badge variant="secondary" className="gap-1.5">
            <MapPin className="h-3 w-3" />
            {job.location}
          </Badge>
        )}
        {job.remote_type && (
          <Badge variant="secondary" className="gap-1.5">
            {job.remote_type.toLowerCase().includes("remote") ? (
              <Wifi className="h-3 w-3" />
            ) : (
              <Building2 className="h-3 w-3" />
            )}
            {job.remote_type}
          </Badge>
        )}
        {job.employment_type && (
          <Badge variant="secondary" className="gap-1.5">
            <Briefcase className="h-3 w-3" />
            {job.employment_type}
          </Badge>
        )}
        {job.experience_level && (
          <Badge variant="secondary" className="gap-1.5">
            <Layers className="h-3 w-3" />
            {job.experience_level}
          </Badge>
        )}
      </div>

      {(job.salary_min || job.salary_max) && (
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <DollarSign className="h-4 w-4 text-emerald-500" />
          <span>{formatSalary(job.salary_min, job.salary_max, job.currency)}</span>
          {job.currency && job.currency !== "USD" && (
            <span className="text-xs text-muted-foreground">({job.currency})</span>
          )}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <Button asChild>
          <a href={job.job_url} target="_blank" rel="noopener noreferrer">
            <ExternalLink className="h-4 w-4" />
            Apply Now
          </a>
        </Button>
        <Button variant="outline">
          <Bookmark className="h-4 w-4" />
          Save Job
        </Button>
        <Button variant="outline" size="sm" asChild>
          <a href="/ats-analyzer">
            <FileText className="h-4 w-4" />
            Analyze JD
          </a>
        </Button>
        <Button variant="outline" size="sm" asChild>
          <a href="/ai-tailor">
            <Sparkles className="h-4 w-4" />
            Tailor Resume
          </a>
        </Button>
      </div>

      <Separator />

      <div>
        <h3 className="mb-3 text-lg font-semibold">About this role</h3>
        <div className="max-h-64 overflow-y-auto whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">
          {job.description_raw || (
            <span className="italic">No description available.</span>
          )}
        </div>
      </div>

      <Separator />

      <div className="space-y-2 text-sm text-muted-foreground">
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4" />
          <span>Posted {formatDate(job.created_at)}</span>
        </div>
        {job.source?.name && (
          <div className="flex items-center gap-2">
            <Building2 className="h-4 w-4" />
            <span>Source: {job.source.name}</span>
          </div>
        )}
        <div className="flex items-center gap-2">
          <Badge variant={getStatusVariant(job.status)} className="text-xs">
            {job.status}
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4" />
          <span>Updated {formatDate(job.updated_at)}</span>
        </div>
      </div>
    </div>
  );
}

function JobPreviewSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <Skeleton className="h-14 w-14 rounded-xl" />
          <div className="space-y-2">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-7 w-56" />
          </div>
        </div>
        <Skeleton className="h-9 w-9" />
      </div>

      <div className="flex flex-wrap gap-2">
        <Skeleton className="h-6 w-24 rounded-md" />
        <Skeleton className="h-6 w-28 rounded-md" />
        <Skeleton className="h-6 w-20 rounded-md" />
        <Skeleton className="h-6 w-32 rounded-md" />
      </div>

      <Skeleton className="h-5 w-48" />

      <div className="flex flex-wrap gap-2">
        <Skeleton className="h-9 w-28 rounded-md" />
        <Skeleton className="h-9 w-28 rounded-md" />
        <Skeleton className="h-8 w-32 rounded-md" />
        <Skeleton className="h-8 w-32 rounded-md" />
      </div>

      <Skeleton className="h-px w-full" />

      <div className="space-y-3">
        <Skeleton className="h-6 w-36" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-2/3" />
      </div>

      <Skeleton className="h-px w-full" />

      <div className="space-y-2">
        <Skeleton className="h-4 w-44" />
        <Skeleton className="h-4 w-36" />
        <Skeleton className="h-5 w-20 rounded-md" />
        <Skeleton className="h-4 w-48" />
      </div>
    </div>
  );
}

export function JobPreview({ jobId, onClose }: JobPreviewProps) {
  const { data: job, isLoading, isError } = useJob(jobId);

  return (
    <AnimatePresence mode="wait">
      {jobId && (
        <motion.div
          key={jobId}
          initial={{ opacity: 0, x: 40 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 40 }}
          transition={{ type: "spring", stiffness: 300, damping: 30, mass: 0.8 }}
          className="sticky top-24 w-full"
          style={{ maxHeight: "calc(100vh - 8rem)" }}
        >
          <div className="h-full overflow-y-auto rounded-xl border bg-card p-6 text-card-foreground shadow">
            {isLoading ? (
              <JobPreviewSkeleton />
            ) : isError || !job ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <p className="text-sm text-muted-foreground">Failed to load job details.</p>
                <Button variant="outline" size="sm" className="mt-4" onClick={onClose}>
                  Close
                </Button>
              </div>
            ) : (
              <JobPreviewContent job={job} onClose={onClose} />
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
