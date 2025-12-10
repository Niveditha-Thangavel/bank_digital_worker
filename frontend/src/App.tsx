import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { NotificationProvider } from "@/contexts/NotificationContext";

import Login from "./pages/Login";
import CustomerLayout from "./layouts/CustomerLayout";
import AdminLayout from "./layouts/AdminLayout";

import CustomerChat from "./pages/customer/Chat";
import CustomerHistory from "./pages/customer/History";
import CustomerRules from "./pages/customer/Rules";
import CustomerSettings from "./pages/customer/Settings";
import CustomerHelp from "./pages/customer/Help";

// AdminChat removed - using FloatingAIAssistant instead
import AdminHistory from "./pages/admin/History";
import AdminCustomerData from "./pages/admin/CustomerData";
import AdminDecisions from "./pages/admin/Decisions";
import AdminNotifications from "./pages/admin/Notifications";
import AdminSettings from "./pages/admin/Settings";

import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <NotificationProvider>
        <TooltipProvider>
          <Toaster />
          <Sonner />
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<Navigate to="/login" replace />} />
              <Route path="/login" element={<Login />} />
              
              {/* Customer Routes */}
              <Route element={<CustomerLayout />}>
                <Route path="/chat" element={<CustomerChat />} />
                <Route path="/history" element={<CustomerHistory />} />
                <Route path="/rules" element={<CustomerRules />} />
                <Route path="/settings" element={<CustomerSettings />} />
                <Route path="/help" element={<CustomerHelp />} />
              </Route>

              {/* Admin Routes */}
              <Route path="/admin" element={<AdminLayout />}>
                <Route index element={<Navigate to="customer-data" replace />} />
                <Route path="chat" element={<Navigate to="/admin/customer-data" replace />} />
                <Route path="history" element={<AdminHistory />} />
                <Route path="customer-data" element={<AdminCustomerData />} />
                <Route path="decisions" element={<AdminDecisions />} />
                <Route path="notifications" element={<AdminNotifications />} />
                <Route path="settings" element={<AdminSettings />} />
              </Route>

              <Route path="*" element={<NotFound />} />
            </Routes>
          </BrowserRouter>
        </TooltipProvider>
      </NotificationProvider>
    </AuthProvider>
  </QueryClientProvider>
);

export default App;
