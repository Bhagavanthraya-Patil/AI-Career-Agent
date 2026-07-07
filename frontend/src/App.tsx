import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import { ThemeProvider } from "@/components/providers/theme-provider";
import { QueryProvider } from "@/components/providers/query-provider";
import { AuthProvider } from "@/components/providers/auth-provider";
import { AppLayout } from "@/components/layout/app-layout";

import Dashboard from "@/pages/dashboard";
import Jobs from "@/pages/jobs";
import Resume from "@/pages/resume";
import AtsAnalyzer from "@/pages/ats-analyzer";
import AiTailor from "@/pages/ai-tailor";
import Applications from "@/pages/applications";
import Tracker from "@/pages/tracker";
import Analytics from "@/pages/analytics";
import Settings from "@/pages/settings";
import NotFound from "@/pages/not-found";

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <QueryProvider>
          <AuthProvider>
            <Routes>
              <Route element={<AppLayout />}>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/jobs" element={<Jobs />} />
                <Route path="/resume" element={<Resume />} />
                <Route path="/ats-analyzer" element={<AtsAnalyzer />} />
                <Route path="/ai-tailor" element={<AiTailor />} />
                <Route path="/applications" element={<Applications />} />
                <Route path="/tracker" element={<Tracker />} />
                <Route path="/analytics" element={<Analytics />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="*" element={<NotFound />} />
              </Route>
            </Routes>
          </AuthProvider>
        </QueryProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}
