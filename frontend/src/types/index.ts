export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
}

export interface Job {
  id: string;
  title: string;
  company: Company;
  source: JobSource;
  location: string;
  remote_type: string;
  employment_type: string;
  experience_level: string;
  salary_min?: number;
  salary_max?: number;
  currency?: string;
  job_url: string;
  description_raw?: string;
  status: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Company {
  id: string;
  name: string;
  website?: string;
  industry?: string;
  logo_url?: string;
  location?: string;
}

export interface JobSource {
  id: string;
  name: string;
  is_active: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApiError {
  detail: string;
  status_code?: number;
}

export interface Application {
  id: string;
  job_id: string;
  job?: Job;
  status: ApplicationStatus;
  apply_url?: string;
  confirmation_code?: string;
  notes?: string;
  rating?: number;
  resume_version?: string;
  cover_letter_version?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type ApplicationStatus =
  | "draft"
  | "ready"
  | "applied"
  | "submitted"
  | "viewed"
  | "assessment"
  | "interview"
  | "technical_interview"
  | "hr_interview"
  | "offer"
  | "accepted"
  | "rejected"
  | "withdrawn"
  | "expired"
  | "failed"
  | "cancelled";

export interface TrackerMetrics {
  total_applications: number;
  success_count: number;
  success_rate: number;
  failure_count: number;
  interview_count: number;
  offer_count: number;
  rejection_count: number;
  pending_count: number;
  by_status: Record<string, number>;
  by_source: Record<string, number>;
  by_company: Record<string, number>;
}

export interface NavigationItem {
  label: string;
  href: string;
  icon: string;
  badge?: number;
}

export interface DashboardStats {
  totalJobs: number;
  appliedJobs: number;
  savedJobs: number;
  interviews: number;
  offers: number;
  rejections: number;
  resumeScore: number;
  atsScore: number;
}

export interface DashboardStat extends DashboardStats {
  trends: {
    totalJobs: number;
    appliedJobs: number;
    savedJobs: number;
    interviews: number;
    offers: number;
    rejections: number;
    resumeScore: number;
    atsScore: number;
  };
}

export interface InsightCard {
  id: string;
  type: "resume" | "ats" | "market" | "skills" | "salary" | "demand";
  title: string;
  description: string;
  score?: number;
  priority: "high" | "medium" | "low";
  action?: string;
}

export interface TimelineEvent {
  id: string;
  type: "application" | "interview" | "offer" | "rejection" | "assessment" | "saved" | "note";
  title: string;
  description: string;
  company?: string;
  companyLogo?: string;
  status: ApplicationStatus;
  timestamp: string;
}

export interface QuickAction {
  id: string;
  label: string;
  description: string;
  icon: string;
  href: string;
  color: string;
}

export interface ChartDataPoint {
  label: string;
  value: number;
}

export interface MarketData {
  skillsDemand: ChartDataPoint[];
  applicationsTrend: ChartDataPoint[];
  salaryTrend: ChartDataPoint[];
}

export interface DashboardNotification {
  id: string;
  type: "activity" | "system" | "recommendation";
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
}
