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
import { useAuth } from './context/AuthContext';

function PrivateRoute({ children }) {
  const { isAuthenticated, isAuthReady } = useAuth();

  if (!isAuthReady) {
    return null;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

function AdminRoute({ children }) {
  const { isAuthenticated, isAdmin, isAuthReady } = useAuth();

  if (!isAuthReady) {
    return null;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!isAdmin) {
    return <Navigate to="/" replace />;
  }

  return children;
}

function AuthPageRoute({ children }) {
  const { isAuthenticated, isAuthReady } = useAuth();

  if (!isAuthReady) {
    return null;
  }

  if (isAuthenticated) {
    return <Navigate to="/profile" replace />;
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
            <Route
              path="/login"
              element={
                <AuthPageRoute>
                  <LoginPage />
                </AuthPageRoute>
              }
            />
            <Route
              path="/register"
              element={
                <AuthPageRoute>
                  <RegisterPage />
                </AuthPageRoute>
              }
            />

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
                  <AdminLayout />
                </AdminRoute>
              }
            >
              <Route index element={<Navigate to="overview" replace />} />
              <Route path="overview" element={<AdminOverviewPage />} />
              <Route path="users" element={<AdminUsersPage />} />
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
