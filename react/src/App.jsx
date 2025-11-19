import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import ErrorBoundary from './ErrorBoundary';
import './App.css';

import { Home } from './components/Home';
import MainLayout from './components/Layout/MainLayout';
import LoginPage from './components/Auth/Login';
import RegisterPage from './components/Auth/Register';
import ProfilePage from './components/Profile';
import AdminMainPage from './components/Admin';
import AdminOverviewPage from './components/Admin/Overview';
import AdminUsersPage from './components/Admin/Users';
import AdminReferralsPage from './components/Admin/Referrals';
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
        '/admin',
        '/admin/overview',
        '/admin/users',
        '/admin/referrals',
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

            <Route
              path="/profile"
              element={
                <PrivateRoute>
                  <ProfilePage />
                </PrivateRoute>
              }
            />

            <Route
              path="/admin"
              element={
                <AdminRoute>
                  <AdminMainPage />
                </AdminRoute>
              }
            />
            <Route
              path="/admin/overview"
              element={
                <AdminRoute>
                  <AdminOverviewPage />
                </AdminRoute>
              }
            />
            <Route
              path="/admin/users"
              element={
                <AdminRoute>
                  <AdminUsersPage />
                </AdminRoute>
              }
            />
            <Route
              path="/admin/referrals"
              element={
                <AdminRoute>
                  <AdminReferralsPage />
                </AdminRoute>
              }
            />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </MainLayout>
      </ErrorBoundary>
    </div>
  );
}

export default App;
