import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const AdminMainPage = () => {
  const navigate = useNavigate();

  useEffect(() => {
    navigate('/admin/overview', { replace: true });
  }, [navigate]);

  return (
    <main
      data-easytag="id1-react/src/components/Admin/index.jsx"
      className="page page-admin"
    >
      <div className="container">
        <div className="card">
          <h1 className="page-title">Админ-панель</h1>
          <p className="page-subtitle">
            Загрузка панели администратора и перенаправление на общий обзор.
          </p>
        </div>
      </div>
    </main>
  );
};

export default AdminMainPage;
