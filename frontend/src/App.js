import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { LanguageProvider } from "@/contexts/LanguageContext";
import { Toaster } from "sonner";
import AppLayout from "@/components/layout/AppLayout";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import TransactionsPage from "@/pages/TransactionsPage";
import TransactionDetailPage from "@/pages/TransactionDetailPage";
import LeavePage from "@/pages/LeavePage";
import AttendancePage from "@/pages/AttendancePage";
import STASMirrorPage from "@/pages/STASMirrorPage";
import EmployeesPage from "@/pages/EmployeesPage";
import EmployeeProfilePage from "@/pages/EmployeeProfilePage";
import SettingsPage from "@/pages/SettingsPage";
import WorkLocationsPage from "@/pages/WorkLocationsPage";
import CustodyPage from "@/pages/CustodyPage";
import FinancialCustodyPage from "@/pages/FinancialCustodyPage";
import CompanySettingsPage from "@/pages/CompanySettingsPage";
import SystemMaintenancePage from "@/pages/SystemMaintenancePage";
import ContractsManagementPage from "@/pages/ContractsManagementPage";
import SettlementPage from "@/pages/SettlementPage";
import MyFinancesPage from "@/pages/MyFinancesPage";
import TeamAttendancePage from "@/pages/TeamAttendancePage";
import PenaltiesPage from "@/pages/PenaltiesPage";
import LoginSessionsPage from "@/pages/LoginSessionsPage";
import TasksPage from "@/pages/TasksPage";
import MaintenanceTrackingPage from "@/pages/MaintenanceTrackingPage";

function ProtectedRoute({ children, allowedRoles }) {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }
  
  // Not logged in - show login page
  if (!user) {
    return <LoginPage />;
  }
  
  if (allowedRoles && !allowedRoles.includes(user.role)) return <Navigate to="/" replace />;
  return <AppLayout>{children}</AppLayout>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      <Route path="/transactions" element={<ProtectedRoute><TransactionsPage /></ProtectedRoute>} />
      <Route path="/transactions/:id" element={<ProtectedRoute><TransactionDetailPage /></ProtectedRoute>} />
      <Route path="/leave" element={<ProtectedRoute><LeavePage /></ProtectedRoute>} />
      <Route path="/attendance" element={<ProtectedRoute><AttendancePage /></ProtectedRoute>} />
      <Route path="/my-finances" element={<ProtectedRoute><MyFinancesPage /></ProtectedRoute>} />
      <Route path="/work-locations" element={<ProtectedRoute allowedRoles={['sultan', 'naif', 'stas']}><WorkLocationsPage /></ProtectedRoute>} />
      <Route path="/custody" element={<ProtectedRoute allowedRoles={['sultan', 'naif', 'stas']}><CustodyPage /></ProtectedRoute>} />
      <Route path="/financial-custody" element={<ProtectedRoute allowedRoles={['sultan', 'naif', 'salah', 'mohammed', 'stas']}><FinancialCustodyPage /></ProtectedRoute>} />
      <Route path="/stas-mirror" element={<ProtectedRoute allowedRoles={['stas']}><STASMirrorPage /></ProtectedRoute>} />
      <Route path="/company-settings" element={<ProtectedRoute allowedRoles={['stas']}><CompanySettingsPage /></ProtectedRoute>} />
      <Route path="/system-maintenance" element={<ProtectedRoute allowedRoles={['stas']}><SystemMaintenancePage /></ProtectedRoute>} />
      <Route path="/contracts-management" element={<ProtectedRoute allowedRoles={['sultan', 'naif', 'stas']}><ContractsManagementPage /></ProtectedRoute>} />
      <Route path="/settlement" element={<ProtectedRoute allowedRoles={['sultan', 'naif', 'stas']}><SettlementPage /></ProtectedRoute>} />
      <Route path="/team-attendance" element={<ProtectedRoute allowedRoles={['sultan', 'naif', 'stas']}><TeamAttendancePage /></ProtectedRoute>} />
      <Route path="/penalties" element={<ProtectedRoute allowedRoles={['sultan', 'naif', 'stas']}><PenaltiesPage /></ProtectedRoute>} />
      <Route path="/login-sessions" element={<ProtectedRoute allowedRoles={['sultan', 'naif', 'stas']}><LoginSessionsPage /></ProtectedRoute>} />
      <Route path="/tasks" element={<ProtectedRoute><TasksPage /></ProtectedRoute>} />
      <Route path="/employees" element={<ProtectedRoute allowedRoles={['sultan', 'naif', 'stas', 'mohammed']}><EmployeesPage /></ProtectedRoute>} />
      <Route path="/employees/:employeeId" element={<ProtectedRoute allowedRoles={['sultan', 'naif', 'stas', 'mohammed']}><EmployeeProfilePage /></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <AuthProvider>
          <BrowserRouter>
            <AppRoutes />
          </BrowserRouter>
          <Toaster position="top-right" richColors closeButton />
        </AuthProvider>
      </LanguageProvider>
    </ThemeProvider>
  );
}

export default App;
