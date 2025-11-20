import React, { useEffect, useState } from 'react';
import {
  fetchAdminMembers,
  createAdminMember,
  updateAdminMember,
} from '../../api/admin';

const initialFormState = {
  firstName: '',
  lastName: '',
  phone: '',
  email: '',
  password: '',
  isInfluencer: false,
  isAdmin: false,
};

const AdminUsersPage = () => {
  const [members, setMembers] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [formState, setFormState] = useState(initialFormState);
  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState('');
  const [formSuccess, setFormSuccess] = useState('');

  const [updateError, setUpdateError] = useState('');

  const loadMembers = async (pageParam) => {
    setLoading(true);
    setError('');

    try {
      const data = await fetchAdminMembers({ page: pageParam });
      const results = Array.isArray(data.results) ? data.results : [];

      setMembers(results);
      setCount(typeof data.count === 'number' ? data.count : results.length);

      const pageSize = results.length > 0 ? results.length : 1;
      const pages = data.count ? Math.max(1, Math.ceil(data.count / pageSize)) : 1;
      setTotalPages(pages);
    } catch (err) {
      console.error('Failed to load admin members', err);
      setError('Не удалось загрузить пользователей. Пожалуйста, попробуйте позже.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMembers(page);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  const handleInputChange = (event) => {
    const { name, value, type, checked } = event.target;

    setFormState((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleCreateMember = async (event) => {
    event.preventDefault();

    setFormLoading(true);
    setFormError('');
    setFormSuccess('');

    try {
      const payload = {
        first_name: formState.firstName,
        last_name: formState.lastName,
        phone: formState.phone,
        email: formState.email || null,
        password: formState.password,
        is_influencer: formState.isInfluencer,
        is_admin: formState.isAdmin,
      };

      await createAdminMember(payload);
      setFormSuccess('Пользователь успешно создан.');
      setFormState(initialFormState);

      // После создания возвращаемся на первую страницу списка
      setPage(1);
      loadMembers(1);
    } catch (err) {
      console.error('Failed to create admin member', err);
      setFormError('Не удалось создать пользователя. Проверьте данные и попробуйте снова.');
    } finally {
      setFormLoading(false);
    }
  };

  const handleToggleFlag = async (id, field, checked) => {
    setUpdateError('');

    try {
      const payload = {
        [field]: checked,
      };

      await updateAdminMember(id, payload);

      setMembers((prev) =>
        prev.map((member) =>
          member.id === id
            ? {
                ...member,
                [field]: checked,
              }
            : member
        )
      );
    } catch (err) {
      console.error('Failed to update member flags', err);
      setUpdateError('Не удалось обновить права пользователя. Попробуйте позже.');
    }
  };

  const handlePrevPage = () => {
    if (page > 1) {
      setPage((prev) => prev - 1);
    }
  };

  const handleNextPage = () => {
    if (page < totalPages) {
      setPage((prev) => prev + 1);
    }
  };

  return (
    <main
      data-easytag="id1-react/src/components/Admin/Users.jsx"
      className="page-admin-users-inner"
    >
      <section className="card admin-section-header">
        <h2 className="section-title">Пользователи</h2>
        <p className="section-subtitle">
          Управление учетными записями пользователей и инфлюенсеров.
        </p>
      </section>

      <section className="card admin-form-card">
        <h3 className="admin-form-title">Создать нового пользователя</h3>
        <p className="admin-form-subtitle">
          Используйте эту форму, чтобы заводить аккаунты инфлюенсеров и администраторов.
        </p>

        <form className="admin-form-grid" onSubmit={handleCreateMember}>
          <div className="admin-form-row">
            <label className="admin-form-label" htmlFor="firstName">
              Имя
            </label>
            <input
              id="firstName"
              name="firstName"
              type="text"
              className="admin-form-input"
              value={formState.firstName}
              onChange={handleInputChange}
              required
            />
          </div>

          <div className="admin-form-row">
            <label className="admin-form-label" htmlFor="lastName">
              Фамилия
            </label>
            <input
              id="lastName"
              name="lastName"
              type="text"
              className="admin-form-input"
              value={formState.lastName}
              onChange={handleInputChange}
              required
            />
          </div>

          <div className="admin-form-row">
            <label className="admin-form-label" htmlFor="phone">
              Телефон
            </label>
            <input
              id="phone"
              name="phone"
              type="tel"
              className="admin-form-input"
              value={formState.phone}
              onChange={handleInputChange}
              required
            />
          </div>

          <div className="admin-form-row">
            <label className="admin-form-label" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              name="email"
              type="email"
              className="admin-form-input"
              value={formState.email}
              onChange={handleInputChange}
            />
          </div>

          <div className="admin-form-row">
            <label className="admin-form-label" htmlFor="password">
              Пароль
            </label>
            <input
              id="password"
              name="password"
              type="password"
              className="admin-form-input"
              value={formState.password}
              onChange={handleInputChange}
              required
            />
          </div>

          <div className="admin-form-row admin-form-row-inline">
            <label className="admin-checkbox-label">
              <input
                type="checkbox"
                name="isInfluencer"
                checked={formState.isInfluencer}
                onChange={handleInputChange}
              />
              <span>Инфлюенсер</span>
            </label>

            <label className="admin-checkbox-label">
              <input
                type="checkbox"
                name="isAdmin"
                checked={formState.isAdmin}
                onChange={handleInputChange}
              />
              <span>Админ</span>
            </label>
          </div>

          {formError && <p className="admin-form-error">{formError}</p>}
          {formSuccess && <p className="admin-form-success">{formSuccess}</p>}

          <div className="admin-form-actions">
            <button
              type="submit"
              className="btn btn-primary"
              disabled={formLoading}
            >
              {formLoading ? 'Создание...' : 'Создать пользователя'}
            </button>
          </div>
        </form>
      </section>

      <section className="card admin-table-card">
        <div className="admin-table-header">
          <div>
            <h3 className="admin-table-title">Список пользователей</h3>
            <p className="admin-table-subtitle">
              Всего пользователей: {count}
            </p>
          </div>
        </div>

        {loading && (
          <p className="admin-table-loading">Загрузка списка пользователей...</p>
        )}

        {error && !loading && <p className="admin-table-error">{error}</p>}
        {updateError && !loading && (
          <p className="admin-table-error">{updateError}</p>
        )}

        {!loading && !error && (
          <div className="table-wrapper">
            <table className="table admin-table">
              <thead>
                <tr>
                  <th>Имя</th>
                  <th>Фамилия</th>
                  <th>Телефон</th>
                  <th>Email</th>
                  <th>Статус</th>
                  <th>Роль</th>
                  <th>Кол-во рефералов</th>
                  <th>Бонусы</th>
                  <th>Заработано денег</th>
                  <th>Инфлюенсер</th>
                  <th>Админ</th>
                </tr>
              </thead>
              <tbody>
                {members.length === 0 && (
                  <tr>
                    <td colSpan={11} className="admin-table-empty">
                      Пользователи не найдены.
                    </td>
                  </tr>
                )}

                {members.map((member) => (
                  <tr key={member.id}>
                    <td>{member.first_name}</td>
                    <td>{member.last_name}</td>
                    <td>{member.phone}</td>
                    <td>{member.email || '—'}</td>
                    <td>{member.is_influencer ? 'Инфлюенсер' : 'Игрок'}</td>
                    <td>{member.is_admin ? 'Админ' : 'Пользователь'}</td>
                    <td>{member.total_referrals}</td>
                    <td>{member.total_bonus_points}</td>
                    <td>{member.total_money_earned} ₽</td>
                    <td>
                      <input
                        type="checkbox"
                        checked={member.is_influencer}
                        onChange={(event) =>
                          handleToggleFlag(
                            member.id,
                            'is_influencer',
                            event.target.checked
                          )
                        }
                      />
                    </td>
                    <td>
                      <input
                        type="checkbox"
                        checked={member.is_admin}
                        onChange={(event) =>
                          handleToggleFlag(
                            member.id,
                            'is_admin',
                            event.target.checked
                          )
                        }
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="admin-pagination">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handlePrevPage}
            disabled={page <= 1 || loading}
          >
            Назад
          </button>
          <span className="admin-pagination-info">
            Страница {page} из {totalPages}
          </span>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleNextPage}
            disabled={page >= totalPages || loading}
          >
            Вперёд
          </button>
        </div>
      </section>
    </main>
  );
};

export default AdminUsersPage;
