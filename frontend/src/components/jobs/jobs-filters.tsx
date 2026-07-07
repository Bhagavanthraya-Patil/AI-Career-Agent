import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search, MapPin, Building2, Globe, ChevronDown, X, SlidersHorizontal,
  Briefcase, Wifi, Layers, DollarSign, Clock, RotateCcw, Check,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from "@/components/ui/select";
import { useJobsStore } from "@/store/jobs-store";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function toggleCommaSep(current: string, value: string): string {
  const arr = current ? current.split(",").filter(Boolean) : [];
  if (arr.includes(value)) return arr.filter((v) => v !== value).join(",");
  return [...arr, value].join(",");
}

function inCommaSep(current: string, value: string): boolean {
  return (current ? current.split(",").filter(Boolean) : []).includes(value);
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SORT_OPTIONS = [
  { label: "Most Recent", sort_by: "scraped_at", sort_order: "desc" as const },
  { label: "Oldest", sort_by: "scraped_at", sort_order: "asc" as const },
  { label: "Highest Salary", sort_by: "salary_min", sort_order: "desc" as const },
  { label: "Lowest Salary", sort_by: "salary_min", sort_order: "asc" as const },
  { label: "Company A-Z", sort_by: "company", sort_order: "asc" as const },
];

const EMPLOYMENT_TYPES = [
  "Full-time",
  "Part-time",
  "Contract",
  "Internship",
  "Freelance",
  "Temporary",
];

const REMOTE_TYPES = [
  { label: "Any", value: "" },
  { label: "Remote", value: "remote" },
  { label: "Hybrid", value: "hybrid" },
  { label: "On-site", value: "on-site" },
];

const EXPERIENCE_LEVELS = ["Entry", "Mid", "Senior", "Lead", "Staff"];

// ---------------------------------------------------------------------------
// FilterSection – collapsible accordion item
// ---------------------------------------------------------------------------

interface FilterSectionProps {
  title: string;
  icon: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

function FilterSection({ title, icon, defaultOpen = false, children }: FilterSectionProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border-b border-border/50 last:border-b-0">
      <button
        type="button"
        onClick={() => setOpen((p) => !p)}
        className="flex w-full items-center justify-between py-2.5 text-sm font-medium text-foreground transition-colors hover:text-foreground/80"
      >
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">{icon}</span>
          <span>{title}</span>
        </div>
        <motion.div
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.2, ease: "easeInOut" }}
        >
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        </motion.div>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="body"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="pb-4 pt-1">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ---------------------------------------------------------------------------
// JobsFilters
// ---------------------------------------------------------------------------

interface JobsFiltersProps {
  className?: string;
  show?: boolean;
  onClose?: () => void;
}

function JobsFilters({ className, show, onClose }: JobsFiltersProps) {
  const { filters, setFilter, setFilters, resetFilters } = useJobsStore();

  // --- debounced search ---------------------------------------------------
  const [searchInput, setSearchInput] = useState(filters.q);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchInput !== filters.q) {
        setFilter("q", searchInput);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput, filters.q, setFilter]);

  // sync if store changes externally (e.g. reset)
  useEffect(() => {
    setSearchInput(filters.q);
  }, [filters.q]);

  // --- active filter count ------------------------------------------------
  const activeCount = useCallback(() => {
    let n = 0;
    if (filters.q) n++;
    if (filters.sort_by !== "scraped_at" || filters.sort_order !== "desc") n++;
    if (filters.remote_type) n++;
    if (filters.employment_type) n++;
    if (filters.experience_level) n++;
    if (filters.salary_min !== null) n++;
    if (filters.salary_max !== null) n++;
    if (filters.location) n++;
    if (filters.company) n++;
    if (filters.source) n++;
    if (filters.status) n++;
    return n;
  }, [filters])();

  // --- current sort index -------------------------------------------------
  const sortIdx = SORT_OPTIONS.findIndex(
    (o) => o.sort_by === filters.sort_by && o.sort_order === filters.sort_order,
  );

  // --- content ------------------------------------------------------------
  const content = (
    <div className={cn("flex flex-col", className)}>
      {/* header */}
      <div className="flex items-center justify-between border-b border-border/50 px-4 py-3">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-semibold">Filters</span>
          {activeCount > 0 && (
            <Badge variant="secondary" className="h-5 px-1.5 text-[10px] leading-none">
              {activeCount}
            </Badge>
          )}
        </div>
        {onClose && (
          <Button variant="ghost" size="icon" onClick={onClose} className="h-7 w-7">
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* body */}
      <div className="flex-1 overflow-y-auto px-4">
        {/* 1. Search */}
        <FilterSection title="Search" icon={<Search className="h-4 w-4" />} defaultOpen>
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Title, keyword, skill…"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="h-9 pl-8"
            />
          </div>
        </FilterSection>

        {/* 2. Sort By */}
        <FilterSection
          title="Sort By"
          icon={<SlidersHorizontal className="h-4 w-4" />}
        >
          <Select
            value={sortIdx >= 0 ? String(sortIdx) : undefined}
            onValueChange={(v) => {
              const opt = SORT_OPTIONS[Number(v)];
              if (opt) {
                setFilters({ sort_by: opt.sort_by, sort_order: opt.sort_order });
              }
            }}
          >
            <SelectTrigger className="h-9 w-full">
              <SelectValue placeholder="Select…" />
            </SelectTrigger>
            <SelectContent>
              {SORT_OPTIONS.map((opt, i) => (
                <SelectItem key={i} value={String(i)}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FilterSection>

        {/* 3. Employment Type */}
        <FilterSection title="Employment Type" icon={<Briefcase className="h-4 w-4" />}>
          <div className="space-y-0.5">
            {EMPLOYMENT_TYPES.map((t) => {
              const checked = inCommaSep(filters.employment_type, t.toLowerCase());
              return (
                <label
                  key={t}
                  className="flex cursor-pointer items-center gap-2.5 rounded px-1 py-1.5 transition-colors hover:bg-accent/50"
                >
                  <div
                    className={cn(
                      "flex h-4 w-4 shrink-0 items-center justify-center rounded-[3px] border transition-colors",
                      checked
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-input",
                    )}
                  >
                    {checked && <Check className="h-3 w-3" />}
                  </div>
                  <span className="text-sm">{t}</span>
                </label>
              );
            })}
          </div>
        </FilterSection>

        {/* 4. Remote Type */}
        <FilterSection title="Remote Type" icon={<Wifi className="h-4 w-4" />}>
          <div className="flex flex-wrap gap-1.5">
            {REMOTE_TYPES.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setFilter("remote_type", opt.value)}
                className={cn(
                  "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                  filters.remote_type === opt.value
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "bg-secondary text-secondary-foreground hover:bg-secondary/70",
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </FilterSection>

        {/* 5. Experience Level */}
        <FilterSection title="Experience Level" icon={<Layers className="h-4 w-4" />}>
          <div className="space-y-0.5">
            {EXPERIENCE_LEVELS.map((lvl) => {
              const checked = inCommaSep(filters.experience_level, lvl.toLowerCase());
              return (
                <label
                  key={lvl}
                  className="flex cursor-pointer items-center gap-2.5 rounded px-1 py-1.5 transition-colors hover:bg-accent/50"
                >
                  <div
                    className={cn(
                      "flex h-4 w-4 shrink-0 items-center justify-center rounded-[3px] border transition-colors",
                      checked
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-input",
                    )}
                  >
                    {checked && <Check className="h-3 w-3" />}
                  </div>
                  <span className="text-sm">{lvl}</span>
                </label>
              );
            })}
          </div>
        </FilterSection>

        {/* 6. Salary Range */}
        <FilterSection title="Salary Range" icon={<DollarSign className="h-4 w-4" />}>
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <span className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
                $
              </span>
              <Input
                type="number"
                placeholder="Min"
                value={filters.salary_min ?? ""}
                onChange={(e) =>
                  setFilter(
                    "salary_min",
                    e.target.value ? Number(e.target.value) : null,
                  )
                }
                className="h-9 pl-6"
              />
            </div>
            <span className="text-xs text-muted-foreground">–</span>
            <div className="relative flex-1">
              <span className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
                $
              </span>
              <Input
                type="number"
                placeholder="Max"
                value={filters.salary_max ?? ""}
                onChange={(e) =>
                  setFilter(
                    "salary_max",
                    e.target.value ? Number(e.target.value) : null,
                  )
                }
                className="h-9 pl-6"
              />
            </div>
          </div>
        </FilterSection>

        {/* 7. Location */}
        <FilterSection title="Location" icon={<MapPin className="h-4 w-4" />}>
          <div className="relative">
            <MapPin className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="City, state, or country…"
              value={filters.location}
              onChange={(e) => setFilter("location", e.target.value)}
              className="h-9 pl-8"
            />
          </div>
        </FilterSection>

        {/* 8. Company */}
        <FilterSection title="Company" icon={<Building2 className="h-4 w-4" />}>
          <div className="relative">
            <Building2 className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Company name…"
              value={filters.company}
              onChange={(e) => setFilter("company", e.target.value)}
              className="h-9 pl-8"
            />
          </div>
        </FilterSection>

        {/* 9. Source */}
        <FilterSection title="Source" icon={<Globe className="h-4 w-4" />}>
          <div className="relative">
            <Globe className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="LinkedIn, Indeed, …"
              value={filters.source}
              onChange={(e) => setFilter("source", e.target.value)}
              className="h-9 pl-8"
            />
          </div>
        </FilterSection>

        {/* 10. Status */}
        <FilterSection title="Status" icon={<Clock className="h-4 w-4" />}>
          <Select
            value={filters.status}
            onValueChange={(v) => setFilter("status", v)}
          >
            <SelectTrigger className="h-9 w-full">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All Statuses</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="inactive">Inactive</SelectItem>
            </SelectContent>
          </Select>
        </FilterSection>
      </div>

      {/* footer – clear */}
      <div className="border-t border-border/50 px-4 py-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            resetFilters();
            setSearchInput("");
          }}
          className="w-full gap-2 text-muted-foreground hover:text-foreground"
        >
          <RotateCcw className="h-4 w-4" />
          Clear Filters
          {activeCount > 0 && (
            <Badge variant="secondary" className="ml-auto h-5 px-1.5 text-[10px] leading-none">
              {activeCount}
            </Badge>
          )}
        </Button>
      </div>
    </div>
  );

  // -----------------------------------------------------------------------
  // Mobile drawer mode
  // -----------------------------------------------------------------------
  if (show && onClose) {
    return (
      <AnimatePresence>
        {show && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="fixed inset-0 z-50 bg-black/50"
              onClick={onClose}
            />
            <motion.div
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 300 }}
              className="fixed inset-y-0 left-0 z-50 flex w-[320px] max-w-[85vw] flex-col bg-background shadow-xl"
            >
              {content}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    );
  }

  return content;
}

export default JobsFilters;

// ---------------------------------------------------------------------------
// JobsFiltersDrawer – convenience wrapper for mobile
// ---------------------------------------------------------------------------

export function JobsFiltersDrawer({
  show,
  onClose,
}: {
  show: boolean;
  onClose: () => void;
}) {
  return (
    <AnimatePresence>
      {show && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 z-50 bg-black/50"
            onClick={onClose}
          />
          <motion.div
            initial={{ x: "-100%" }}
            animate={{ x: 0 }}
            exit={{ x: "-100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="fixed inset-y-0 left-0 z-50 flex w-[320px] max-w-[85vw] flex-col bg-background shadow-xl"
          >
            <div className="flex items-center justify-between border-b border-border/50 px-4 py-3">
              <div className="flex items-center gap-2">
                <SlidersHorizontal className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-semibold">Filters</span>
              </div>
              <Button variant="ghost" size="icon" onClick={onClose} className="h-7 w-7">
                <X className="h-4 w-4" />
              </Button>
            </div>
            <JobsFilters className="border-0" />
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
