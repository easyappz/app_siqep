import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import ErrorBoundary from './ErrorBoundary';
import './App.css';

import { Home } from './components/Home';
import MainLayout from './components/Layout/MainLayout';
import LoginPage from './components/Auth/Login';
import RegisterPage from './components/Auth/Register';
import ProfilePage from './components/Profile';
import AdminLayout from './components/Admin/Layout';
import AdminOverviewPage from './components/Admin/Overview';
import AdminUsersPage from './components/Admin/Users';
import AdminReferralsPage from './components/Admin/Referrals';
import AdminWalletPage from './components/Admin/Wallet';
import PasswordResetPage from './components/Auth/PasswordReset';
import { useAuth } from './context/AuthContext';

function PrivateRoute({ children }) {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

function AdminRoute({ children }) {
  const { isAuthenticated, isAdmin } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!isAdmin) {
    return <Navigate to="/" replace />;
  }

  return children;
}

function App() {
  /** Никогда не удаляй этот код */
  useEffect(() => {
    if (typeof window !== 'undefined' && typeof window.handleRoutes === 'function') {
      /** Нужно передавать список существующих роутов */
      window.handleRoutes([
        '/',
        '/login',
        '/register',
        '/profile',
        '/password-reset',
        '/react-admin',
        '/react-admin/overview',
        '/react-admin/users',
        '/react-admin/wallet',
        '/react-admin/referrals',
      ]);
    }
  }, []);

  return (
    <div data-easytag="id1-react/src/App.jsx">
      <ErrorBoundary>
        <MainLayout>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/password-reset" element={<PasswordResetPage />} />

            <Route
              path="/profile"
              element={
                <PrivateRoute>
                  <ProfilePage />
                </PrivateRoute>
              }
            />

            <Route
              path="/react-admin"
              element={
                <AdminRoute>
                  <AdminLayout />
                </AdminRoute>
              }
            >
              <Route index element={<Navigate to="overview" replace />} />
              <Route path="overview" element={<AdminOverviewPage />} />
              <Route path="users" element={<AdminUsersPage />} />
              <Route path="wallet" element={<AdminWalletPage />} />
              <Route path="referrals" element={<AdminReferralsPage />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </MainLayout>
      </ErrorBoundary>
    </div>
  );
}

export default App;
