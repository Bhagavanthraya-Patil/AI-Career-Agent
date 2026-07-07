import { motion } from "framer-motion";

import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { mockMarketData } from "@/data/dashboard";

interface MarketOverviewProps {
  className?: string;
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

export function MarketOverview({ className }: MarketOverviewProps) {
  const { skillsDemand, applicationsTrend, salaryTrend } = mockMarketData;
  const maxApplications = Math.max(...applicationsTrend.map((d) => d.value));
  const maxSalary = Math.max(...salaryTrend.map((d) => d.value));

  return (
    <div className={cn("space-y-4", className)}>
      <div>
        <h2 className="text-lg font-semibold">Market Overview</h2>
        <p className="text-sm text-muted-foreground">
          Skills demand, application trends, and salary benchmarks
        </p>
      </div>

      <motion.div
        variants={containerVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true }}
        className="grid gap-4 md:grid-cols-2 lg:grid-cols-3"
      >
        <motion.div variants={itemVariants}>
          <Card className="border-border/50 shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                Skills Demand
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {skillsDemand.map((skill) => (
                <div key={skill.label} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium">{skill.label}</span>
                    <span className="text-muted-foreground">{skill.value}%</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-muted">
                    <motion.div
                      initial={{ width: 0 }}
                      whileInView={{ width: `${skill.value}%` }}
                      viewport={{ once: true }}
                      transition={{
                        duration: 1,
                        delay: 0.1,
                        ease: "easeOut",
                      }}
                      className={cn(
                        "h-full rounded-full",
                        skill.value >= 80
                          ? "bg-success"
                          : skill.value >= 60
                            ? "bg-warning"
                            : "bg-info",
                      )}
                    />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={itemVariants}>
          <Card className="border-border/50 shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                Applications Trend
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-end justify-between gap-1" style={{ height: 160 }}>
                {applicationsTrend.map((item) => {
                  const heightPct = (item.value / maxApplications) * 100;
                  return (
                    <div
                      key={item.label}
                      className="flex flex-1 flex-col items-center gap-1"
                    >
                      <motion.div
                        initial={{ height: 0 }}
                        whileInView={{ height: `${heightPct}%` }}
                        viewport={{ once: true }}
                        transition={{
                          duration: 0.8,
                          delay: 0.1,
                          ease: "easeOut",
                        }}
                        className="w-full rounded-t-sm bg-primary"
                        style={{ maxHeight: "100%" }}
                      />
                      <span className="text-[10px] text-muted-foreground">
                        {item.label}
                      </span>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={itemVariants}>
          <Card className="border-border/50 shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                Salary Trend
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="relative" style={{ height: 160 }}>
                <svg
                  viewBox={`0 0 ${salaryTrend.length - 1} 100`}
                  preserveAspectRatio="none"
                  className="h-full w-full"
                >
                  <motion.polyline
                    points={salaryTrend
                      .map(
                        (d, i) =>
                          `${i},${100 - (d.value / maxSalary) * 90 - 5}`,
                      )
                      .join(" ")}
                    fill="none"
                    stroke="hsl(var(--primary))"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    initial={{ pathLength: 0 }}
                    whileInView={{ pathLength: 1 }}
                    viewport={{ once: true }}
                    transition={{ duration: 1.5, ease: "easeOut" }}
                  />
                  {salaryTrend.map((d, i) => {
                    const y = 100 - (d.value / maxSalary) * 90 - 5;
                    return (
                      <motion.circle
                        key={d.label}
                        cx={i}
                        cy={y}
                        r="2.5"
                        fill="hsl(var(--background))"
                        stroke="hsl(var(--primary))"
                        strokeWidth="2"
                        initial={{ opacity: 0 }}
                        whileInView={{ opacity: 1 }}
                        viewport={{ once: true }}
                        transition={{ delay: 1.2 + i * 0.1 }}
                      />
                    );
                  })}
                </svg>
                <div className="mt-2 flex justify-between">
                  {salaryTrend.map((d) => (
                    <span
                      key={d.label}
                      className="text-[10px] text-muted-foreground"
                    >
                      {d.label}
                    </span>
                  ))}
                </div>
                <div className="mt-1 flex justify-between">
                  {salaryTrend.map((d) => (
                    <span
                      key={d.label}
                      className="text-[10px] font-medium tabular-nums text-muted-foreground"
                    >
                      ${d.value}k
                    </span>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>
    </div>
  );
}
