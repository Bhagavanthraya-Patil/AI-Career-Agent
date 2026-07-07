import { motion } from "framer-motion";
import { User, Bell, Palette } from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Separator } from "@/components/ui/separator";
import { useThemeStore, type Theme } from "@/store/theme-store";

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

function SettingsSection({
  icon,
  title,
  description,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start gap-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
          {icon}
        </div>
        <div>
          <CardTitle className="text-base">{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </div>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

export default function Settings() {
  const { theme, setTheme } = useThemeStore();

  const themeOptions: { value: Theme; label: string }[] = [
    { value: "light", label: "Light" },
    { value: "dark", label: "Dark" },
    { value: "system", label: "System" },
  ];

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-8"
    >
      <motion.div variants={itemVariants}>
        <PageHeader
          title="Settings"
          description="Manage your preferences"
        />
      </motion.div>

      <motion.div variants={itemVariants} className="space-y-6 max-w-2xl">
        <SettingsSection
          icon={<User className="h-5 w-5" />}
          title="Profile"
          description="Update your personal information and avatar."
        >
          <div className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <div className="h-9 rounded-md border border-input bg-transparent px-3 py-1 text-sm flex items-center text-muted-foreground">
                  Your Name
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <div className="h-9 rounded-md border border-input bg-transparent px-3 py-1 text-sm flex items-center text-muted-foreground">
                  your@email.com
                </div>
              </div>
            </div>
            <Button variant="outline" size="sm">
              Edit Profile
            </Button>
          </div>
        </SettingsSection>

        <SettingsSection
          icon={<Bell className="h-5 w-5" />}
          title="Notifications"
          description="Configure how you receive notifications."
        >
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <p className="text-sm font-medium">Email Notifications</p>
                <p className="text-xs text-muted-foreground">
                  Receive updates via email
                </p>
              </div>
              <Button variant="outline" size="sm">
                Configure
              </Button>
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <p className="text-sm font-medium">Push Notifications</p>
                <p className="text-xs text-muted-foreground">
                  Receive updates in browser
                </p>
              </div>
              <Button variant="outline" size="sm">
                Configure
              </Button>
            </div>
          </div>
        </SettingsSection>

        <SettingsSection
          icon={<Palette className="h-5 w-5" />}
          title="Appearance"
          description="Customize the look and feel of the application."
        >
          <RadioGroup
            value={theme}
            onValueChange={(value) => setTheme(value as Theme)}
            className="flex gap-4"
          >
            {themeOptions.map((option) => (
              <div key={option.value}>
                <RadioGroupItem
                  value={option.value}
                  id={`theme-${option.value}`}
                  className="peer sr-only"
                />
                <Label
                  htmlFor={`theme-${option.value}`}
                  className="flex cursor-pointer flex-col items-center gap-2 rounded-lg border border-border px-6 py-4 peer-data-[state=checked]:border-primary peer-data-[state=checked]:bg-primary/5"
                >
                  <div className="text-sm font-medium">{option.label}</div>
                </Label>
              </div>
            ))}
          </RadioGroup>
        </SettingsSection>
      </motion.div>
    </motion.div>
  );
}
