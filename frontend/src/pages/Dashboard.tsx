import React from 'react';
import { useAuth } from '../hooks/useAuth';
import { PersonalDashboard } from './PersonalDashboard';
import { EmployeeDashboard } from './EmployeeDashboard';
import { AdminDashboard } from './AdminDashboard';

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const role = user?.role?.name;

  if (role === 'ADMIN') {
    return <AdminDashboard />;
  }

  if (role === 'EMPLOYEE') {
    return <EmployeeDashboard />;
  }

  // Default to Personal Dashboard for INDIVIDUAL or fallback
  return <PersonalDashboard />;
};

export default Dashboard;
