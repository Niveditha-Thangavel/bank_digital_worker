import { MessageSquare, History, FileText, Settings, HelpCircle, LogOut, LayoutDashboard, Bell, Users, Database } from 'lucide-react';
import { NavLink } from '@/components/NavLink';
import { useAuth } from '@/contexts/AuthContext';
import { useNotifications } from '@/contexts/NotificationContext';
import { cn } from '@/lib/utils';

const customerNavItems = [
  { title: 'Chat', url: '/chat', icon: MessageSquare },
  { title: 'History', url: '/history', icon: History },
  { title: 'Rules', url: '/rules', icon: FileText },
  { title: 'Settings', url: '/settings', icon: Settings },
  { title: 'Help', url: '/help', icon: HelpCircle },
];

const adminNavItems = [
  { title: 'History', url: '/admin/history', icon: History },
  { title: 'Customer Data', url: '/admin/customer-data', icon: Database },
  { title: 'Decisions', url: '/admin/decisions', icon: LayoutDashboard },
  { title: 'Notifications', url: '/admin/notifications', icon: Bell },
  { title: 'Settings', url: '/admin/settings', icon: Settings },
];

export function AppSidebar() {
  const { user, logout } = useAuth();
  const { unreadCount } = useNotifications();
  
  const navItems = user?.role === 'admin' ? adminNavItems : customerNavItems;
  const initials = user?.role === 'admin' ? 'AD' : user?.customerId?.slice(0, 2) || 'BA';

  return (
    <aside className="w-60 bg-sidebar flex flex-col h-screen sticky top-0">
      {/* Header */}
      <div className="p-4 border-b border-sidebar-border">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-sidebar-accent flex items-center justify-center text-sidebar-foreground font-semibold text-sm">
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-sidebar-foreground font-semibold text-sm truncate">Banking Agent</h1>
            <p className="text-sidebar-foreground/70 text-xs truncate">
              {user?.role === 'admin' ? 'Admin Portal' : `Welcome, ${user?.customerId}`}
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.title}
            to={item.url}
            className="sidebar-item"
            activeClassName="sidebar-item-active"
          >
            <item.icon className="w-5 h-5" />
            <span className="flex-1">{item.title}</span>
            {item.title === 'Notifications' && unreadCount > 0 && (
              <span className="bg-destructive text-destructive-foreground text-xs rounded-full px-2 py-0.5 font-medium">
                {unreadCount}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-sidebar-border">
        <button
          onClick={logout}
          className="sidebar-item w-full text-left hover:bg-destructive/20"
        >
          <LogOut className="w-5 h-5" />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
}
