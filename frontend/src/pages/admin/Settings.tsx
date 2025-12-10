import { useState } from 'react';
import { User, Bell, Shield, Database, Server, Moon, Sun, Monitor, Check } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { useAuth } from '@/contexts/AuthContext';
import { cn } from '@/lib/utils';

type Theme = 'light' | 'dark' | 'system';

export default function AdminSettings() {
  const { user } = useAuth();
  const [theme, setTheme] = useState<Theme>('light');
  const [notifications, setNotifications] = useState({
    email: true,
    push: true,
    customerMessages: true,
    systemAlerts: true
  });

  const themeOptions = [
    { value: 'light', label: 'Light', icon: Sun },
    { value: 'dark', label: 'Dark', icon: Moon },
    { value: 'system', label: 'System', icon: Monitor }
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-border bg-card">
        <h2 className="font-semibold text-foreground">Admin Settings</h2>
        <p className="text-sm text-muted-foreground">Manage system preferences</p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 scrollbar-thin space-y-6">
        {/* Profile */}
        <section>
          <h3 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
            <User className="w-4 h-4" />
            Admin Profile
          </h3>
          <Card className="p-4">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-xl font-semibold">
                AD
              </div>
              <div>
                <h4 className="font-medium text-foreground">{user?.name}</h4>
                <p className="text-sm text-muted-foreground">{user?.email}</p>
                <span className="inline-block mt-1 text-xs bg-primary/10 text-primary px-2 py-0.5 rounded">
                  Administrator
                </span>
              </div>
            </div>
          </Card>
        </section>

        {/* Appearance */}
        <section>
          <h3 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
            <Sun className="w-4 h-4" />
            Appearance
          </h3>
          <Card className="p-4">
            <p className="text-sm text-foreground mb-3">Theme</p>
            <div className="flex gap-2">
              {themeOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setTheme(option.value as Theme)}
                  className={cn(
                    'flex items-center gap-2 px-4 py-2 rounded-lg border transition-all',
                    theme === option.value
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border text-muted-foreground hover:border-primary/50'
                  )}
                >
                  <option.icon className="w-4 h-4" />
                  <span className="text-sm">{option.label}</span>
                  {theme === option.value && <Check className="w-4 h-4" />}
                </button>
              ))}
            </div>
          </Card>
        </section>

        {/* Notifications */}
        <section>
          <h3 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
            <Bell className="w-4 h-4" />
            Notifications
          </h3>
          <Card className="divide-y divide-border">
            <div className="p-4 flex items-center justify-between">
              <div>
                <p className="font-medium text-foreground">Email Notifications</p>
                <p className="text-sm text-muted-foreground">Receive updates via email</p>
              </div>
              <Switch
                checked={notifications.email}
                onCheckedChange={(checked) => setNotifications({ ...notifications, email: checked })}
              />
            </div>
            <div className="p-4 flex items-center justify-between">
              <div>
                <p className="font-medium text-foreground">Push Notifications</p>
                <p className="text-sm text-muted-foreground">Receive browser notifications</p>
              </div>
              <Switch
                checked={notifications.push}
                onCheckedChange={(checked) => setNotifications({ ...notifications, push: checked })}
              />
            </div>
            <div className="p-4 flex items-center justify-between">
              <div>
                <p className="font-medium text-foreground">Customer Messages</p>
                <p className="text-sm text-muted-foreground">Get notified when customers send messages</p>
              </div>
              <Switch
                checked={notifications.customerMessages}
                onCheckedChange={(checked) => setNotifications({ ...notifications, customerMessages: checked })}
              />
            </div>
            <div className="p-4 flex items-center justify-between">
              <div>
                <p className="font-medium text-foreground">System Alerts</p>
                <p className="text-sm text-muted-foreground">Important system notifications</p>
              </div>
              <Switch
                checked={notifications.systemAlerts}
                onCheckedChange={(checked) => setNotifications({ ...notifications, systemAlerts: checked })}
              />
            </div>
          </Card>
        </section>

        {/* Security */}
        <section>
          <h3 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
            <Shield className="w-4 h-4" />
            Security
          </h3>
          <Card className="p-4 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-foreground">Change Password</p>
                <p className="text-sm text-muted-foreground">Update your admin password</p>
              </div>
              <Button variant="outline" size="sm">Change</Button>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-foreground">Two-Factor Authentication</p>
                <p className="text-sm text-muted-foreground">Add an extra layer of security</p>
              </div>
              <Button variant="outline" size="sm">Enable</Button>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-foreground">Session Management</p>
                <p className="text-sm text-muted-foreground">View and manage active sessions</p>
              </div>
              <Button variant="outline" size="sm">Manage</Button>
            </div>
          </Card>
        </section>

        {/* System */}
        <section>
          <h3 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
            <Server className="w-4 h-4" />
            System
          </h3>
          <Card className="p-4 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-foreground">API Configuration</p>
                <p className="text-sm text-muted-foreground">Backend: http://localhost:8000</p>
              </div>
              <Button variant="outline" size="sm">Configure</Button>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-foreground">Database Status</p>
                <p className="text-sm text-muted-foreground">View database connection status</p>
              </div>
              <span className="flex items-center gap-1.5 text-sm text-success">
                <span className="w-2 h-2 rounded-full bg-success" />
                Connected
              </span>
            </div>
          </Card>
        </section>
      </div>
    </div>
  );
}
