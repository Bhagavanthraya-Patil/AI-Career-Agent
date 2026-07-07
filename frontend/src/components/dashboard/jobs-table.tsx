import { useState, useMemo } from "react";
import { motion } from "framer-motion";
import {
  Search,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  MapPin,
  Clock,
  Building2,
} from "lucide-react";

import { cn, formatRelativeTime } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { mockRecentJobs } from "@/data/dashboard";

type SortField = "title" | "company" | "salary" | "date";

interface JobsTableProps {
  className?: string;
}

function formatSalary(min?: number, max?: number, currency?: string): string {
  const curr = currency ?? "USD";
  const fmt = (val: number) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: curr,
      maximumFractionDigits: 0,
    }).format(val);
  if (min && max) return `${fmt(min)} - ${fmt(max)}`;
  if (min) return `From ${fmt(min)}`;
  if (max) return `Up to ${fmt(max)}`;
  return "N/A";
}

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

const sortableColumns: { field: SortField; label: string; className?: string }[] = [
  { field: "company", label: "Company", className: "w-[140px]" },
  { field: "title", label: "Job Title" },
  { field: "salary", label: "Salary", className: "w-[140px]" },
  { field: "date", label: "Posted", className: "w-[100px]" },
];

export function JobsTable({ className }: JobsTableProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [sortField, setSortField] = useState<SortField>("date");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  const filtered = useMemo(() => {
    if (!searchQuery.trim()) return mockRecentJobs;
    const q = searchQuery.toLowerCase();
    return mockRecentJobs.filter(
      (job) =>
        job.title.toLowerCase().includes(q) ||
        job.company.name.toLowerCase().includes(q) ||
        job.location.toLowerCase().includes(q),
    );
  }, [searchQuery]);

  const sorted = useMemo(() => {
    const sortedJobs = [...filtered];
    sortedJobs.sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case "title":
          cmp = a.title.localeCompare(b.title);
          break;
        case "company":
          cmp = a.company.name.localeCompare(b.company.name);
          break;
        case "salary":
          cmp = (a.salary_min ?? 0) - (b.salary_min ?? 0);
          break;
        case "date":
          cmp =
            new Date(a.created_at).getTime() -
            new Date(b.created_at).getTime();
          break;
      }
      return sortDirection === "asc" ? cmp : -cmp;
    });
    return sortedJobs;
  }, [filtered, sortField, sortDirection]);

  function handleSort(field: SortField) {
    if (field === sortField) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  }

  function SortIcon({ field }: { field: SortField }) {
    if (field !== sortField) return <ArrowUpDown className="h-3 w-3 opacity-40" />;
    return sortDirection === "asc" ? (
      <ArrowUp className="h-3 w-3" />
    ) : (
      <ArrowDown className="h-3 w-3" />
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-lg font-semibold">Recent Jobs</h2>
        <div className="relative w-full max-w-xs">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by title, company..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-9 pl-9"
          />
        </div>
      </div>

      <div className="hidden items-center gap-4 rounded-lg border bg-muted/50 px-5 py-2.5 text-xs font-medium text-muted-foreground md:flex">
        <div className="w-[140px]">
          <button
            onClick={() => handleSort("company")}
            className="flex items-center gap-1 hover:text-foreground"
          >
            Company <SortIcon field="company" />
          </button>
        </div>
        <div className="flex-1">
          <button
            onClick={() => handleSort("title")}
            className="flex items-center gap-1 hover:text-foreground"
          >
            Job Title <SortIcon field="title" />
          </button>
        </div>
        <div className="w-[130px] text-center">Location</div>
        <div className="w-[140px] text-right">
          <button
            onClick={() => handleSort("salary")}
            className="flex items-center gap-1 hover:text-foreground"
          >
            Salary <SortIcon field="salary" />
          </button>
        </div>
        <div className="w-[100px] text-right">
          <button
            onClick={() => handleSort("date")}
            className="flex items-center gap-1 hover:text-foreground"
          >
            Posted <SortIcon field="date" />
          </button>
        </div>
        <div className="w-[90px] text-center">Status</div>
      </div>

      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="space-y-2"
      >
        {sorted.map((job) => (
          <motion.div key={job.id} variants={itemVariants}>
            <Card className="border-border/50 shadow-sm transition-colors hover:border-border">
              <CardContent className="p-4">
                <div className="flex flex-col gap-2 md:flex-row md:items-center md:gap-4">
                  <div className="flex min-w-[140px] items-center gap-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <Building2 className="h-4 w-4" />
                    </div>
                    <span className="truncate text-sm font-medium">
                      {job.company.name}
                    </span>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-semibold">{job.title}</p>
                  </div>
                  <div className="flex items-center gap-1 text-xs text-muted-foreground md:w-[130px] md:justify-center">
                    <MapPin className="h-3 w-3 shrink-0" />
                    <span className="truncate">{job.location}</span>
                  </div>
                  <div className="text-right text-xs font-medium tabular-nums text-muted-foreground md:w-[140px]">
                    {formatSalary(job.salary_min, job.salary_max, job.currency)}
                  </div>
                  <div className="flex items-center gap-1 text-xs text-muted-foreground md:w-[100px] md:justify-end">
                    <Clock className="h-3 w-3 shrink-0" />
                    {formatRelativeTime(job.created_at)}
                  </div>
                  <div className="md:w-[90px] md:text-center">
                    <Badge
                      variant={
                        job.status === "active" ? "success" : "secondary"
                      }
                      className="text-[10px]"
                    >
                      {job.status === "active" ? "Active" : job.status}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </motion.div>
    </div>
  );
}
