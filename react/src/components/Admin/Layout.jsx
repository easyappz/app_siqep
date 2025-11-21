import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

const AdminLayout = () => {
  const { member } = useAuth();

  const getNavLinkClassName = ({ isActive }) => {
    const baseClass = 'admin-nav-link';
    return isActive ? `${baseClass} admin-nav-link-active` : baseClass;
  };

  return (
    <div
      data-easytag="id1-react/src/components/Admin/Layout.jsx"
      className="page page-admin"
    >
      <div className="container">
        <header className="admin-header card">
          <div className="admin-header-main">
            <div>
              <h1 className="page-title">Админ-панель</h1>
              <p className="page-subtitle">
                Управление пользователями, рефералами и аналитикой.
              </p>
            </div>
            {member && (
              <div className="admin-header-user">
                <span className="admin-header-user-label">Администратор</span>
                <span className="admin-header-user-name">
                  {member.first_name} {member.last_name}
                </span>
              </div>
            )}
          </div>

          <nav className="admin-nav">
            <NavLink to="/react-admin/overview" className={getNavLinkClassName} end>
              Общая статистика
            </NavLink>
            <NavLink to="/react-admin/users" className={getNavLinkClassName}>
              Пользователи
            </NavLink>
            <NavLink to="/react-admin/wallet" className={getNavLinkClassName}>
              Баланс пользователей
            </NavLink>
            <NavLink to="/react-admin/referrals" className={getNavLinkClassName}>
              Рефералы
            </NavLink>
          </nav>
        </header>

        <section className="admin-content">
          <Outlet />
        </section>
      </div>
    </div>
  );
};

export default AdminLayout;
