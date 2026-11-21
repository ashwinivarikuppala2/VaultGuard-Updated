import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './contexts/AuthContext';
import { ToastProvider } from './contexts/ToastContext';
import { AuthLayout } from './layouts/AuthLayout';
import { DashboardLayout } from './layouts/DashboardLayout';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { PersonalDashboard } from './pages/PersonalDashboard';
import { EmployeeDashboard } from './pages/EmployeeDashboard';
import { AdminDashboard } from './pages/AdminDashboard';
import { Organizations } from './pages/Organizations';
import { Devices } from './pages/Devices';
import { Profile } from './pages/Profile';
import { Settings } from './pages/Settings';
import { BackupCenter } from './pages/BackupCenter';
import { EmployeeBackupDetails } from './pages/EmployeeBackupDetails';
import { BackupJobs } from './pages/BackupJobs';
import { ProtectedFolders } from './pages/ProtectedFolders';
import { VersionHistory } from './pages/VersionHistory';
import { StorageAnalytics } from './pages/StorageAnalytics';
import { BackupPolicies } from './pages/BackupPolicies';
import { ThreatDashboard } from './pages/ThreatDashboard';
import { DetectionHistory } from './pages/DetectionHistory';
import { LiveEvents } from './pages/LiveEvents';
import { AlertCenter } from './pages/AlertCenter';
import { QuarantineCenter } from './pages/QuarantineCenter';
import { ThreatAnalytics } from './pages/ThreatAnalytics';
import { RiskPolicies } from './pages/RiskPolicies';
import { RecoveryCenter } from './pages/RecoveryCenter';
import { RansomwareProtection } from './pages/RansomwareProtection';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <ToastProvider>
            <Routes>
            {/* Public Auth Routes */}
            <Route element={<AuthLayout />}>
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
            </Route>

            {/* Authenticated Dashboard Routes */}
            <Route element={<DashboardLayout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/dashboard" element={<PersonalDashboard />} />
              <Route path="/admin/dashboard" element={<AdminDashboard />} />
              <Route path="/employee/dashboard" element={<EmployeeDashboard />} />
              <Route path="/organizations" element={<Organizations />} />
              <Route path="/devices" element={<Devices />} />
              <Route path="/backups" element={<BackupCenter />} />
              <Route path="/backups/employees/:employeeId" element={<EmployeeBackupDetails />} />
              <Route path="/backup-jobs" element={<BackupJobs />} />
              <Route path="/protected-folders" element={<ProtectedFolders />} />
              <Route path="/version-history" element={<VersionHistory />} />
              <Route path="/storage-analytics" element={<StorageAnalytics />} />
              <Route path="/backup-policies" element={<BackupPolicies />} />
              <Route path="/threats" element={<ThreatDashboard />} />
              <Route path="/detections" element={<DetectionHistory />} />
              <Route path="/live-events" element={<LiveEvents />} />
              <Route path="/alerts" element={<AlertCenter />} />
              <Route path="/quarantine" element={<QuarantineCenter />} />
              <Route path="/threat-analytics" element={<ThreatAnalytics />} />
              <Route path="/risk-policies" element={<RiskPolicies />} />
              <Route path="/recovery" element={<RecoveryCenter />} />
              <Route path="/dashboard/ransomware" element={<RansomwareProtection />} />
              <Route path="/employee/ransomware" element={<RansomwareProtection />} />
              <Route path="/admin/ransomware" element={<RansomwareProtection />} />
              <Route path="/ransomware" element={<RansomwareProtection />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/settings" element={<Settings />} />
            </Route>

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;

