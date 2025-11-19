import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

const MainLayout = ({ children }) => {
  const { isAuthenticated, isAdmin, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div
      data-easytag="id1-react/src/components/Layout/MainLayout.jsx"
      className="app-root"
    >
      <header className="layout-header">
        <div className="container layout-header-inner">
          <div className="layout-logo">Referral Service</div>

          <nav className="layout-nav">
            <NavLink
              to="/"
              className={({ isActive }) =>
                `layout-nav-link${isActive ? ' active' : ''}`
              }
            >
              Главная
            </NavLink>

            {isAuthenticated && (
              <NavLink
                to="/profile"
                className={({ isActive }) =>
                  `layout-nav-link${isActive ? ' active' : ''}`
                }
              >
                Профиль
              </NavLink>
            )}

            {isAdmin && (
              <NavLink
                to="/admin/overview"
                className={({ isActive }) =>
                  `layout-nav-link${isActive ? ' active' : ''}`
                }
              >
                Админ-панель
              </NavLink>
            )}
          </nav>

          <div className="layout-header-actions">
            {isAuthenticated ? (
              <button
                type="button"
                className="btn btn-outline"
                onClick={handleLogout}
              >
                Выйти
              </button>
            ) : (
              <NavLink to="/login" className="btn btn-primary">
                Войти
              </NavLink>
            )}
          </div>
        </div>
      </header>

      <main className="layout-main">{children}</main>

      <footer className="layout-footer">
        <div className="container">
          <p>© {new Date().getFullYear()} Реферальный сервис. Все права защищены.</p>
        </div>
      </footer>
    </div>
  );
};

export default MainLayout;
