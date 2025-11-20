import React, { useEffect, useState } from 'react';
import {
  fetchAdminMembers,
  createAdminMember,
  updateAdminMember,
  resetMemberPassword,
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

  const [resetModalMemberId, setResetModalMemberId] = useState(null);
  const [resetCustomPassword, setResetCustomPassword] = useState('');
  const [resetResultPassword, setResetResultPassword] = useState('');
  const [resetLoading, setResetLoading] = useState(false);
  const [resetError, setResetError] = useState('');
  const [resetSuccess, setResetSuccess] = useState('');

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
      setUpdateError('Не удалось обновить статус пользователя. Попробуйте позже.');
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

  const openResetModal = (memberId) => {
    setResetModalMemberId(memberId);
    setResetCustomPassword('');
    setResetResultPassword('');
    setResetLoading(false);
    setResetError('');
    setResetSuccess('');
  };

  const closeResetModal = () => {
    setResetModalMemberId(null);
    setResetCustomPassword('');
    setResetResultPassword('');
    setResetLoading(false);
    setResetError('');
    setResetSuccess('');
  };

  const handleConfirmReset = async () => {
    if (!resetModalMemberId) {
      return;
    }

    setResetLoading(true);
    setResetError('');
    setResetSuccess('');
    setResetResultPassword('');

    try {
      const payload = {};
      const trimmedPassword = resetCustomPassword ? resetCustomPassword.trim() : '';

      if (trimmedPassword) {
        payload.new_password = trimmedPassword;
      }

      const data = await resetMemberPassword(resetModalMemberId, payload);

      const generated = data && data.generated_password ? String(data.generated_password) : '';
      const detail = data && data.detail
        ? data.detail
        : 'Пароль пользователя успешно сброшен администратором.';

      setResetSuccess(detail);
      setResetResultPassword(generated);
    } catch (err) {
      console.error('Failed to reset member password', err);
      const responseData = err && err.response && err.response.data ? err.response.data : null;
      let message = 'Не удалось сбросить пароль. Попробуйте ещё раз.';

      if (responseData) {
        if (responseData.new_password) {
          const value = Array.isArray(responseData.new_password)
            ? responseData.new_password[0]
            : responseData.new_password;
          message = String(value);
        } else if (responseData.detail && typeof responseData.detail === 'string') {
          message = responseData.detail;
        }
      }

      setResetError(message);
    } finally {
      setResetLoading(false);
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
          Управление учетными записями игроков, инфлюенсеров и администраторов.
        </p>
      </section>

      <section className="card admin-form-card">
        <h3 className="admin-form-title">Создать нового пользователя</h3>
        <p className="admin-form-subtitle">
          Используйте эту форму, чтобы заводить аккаунты игроков, инфлюенсеров и администраторов.
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
            <p className="admin-table-helper">
              Если отметить игрока как инфлюенсера, все его будущие реферальные депозиты
              будут начисляться по правилам программы для инфлюенсеров. Уже созданные
              реферальные события не изменятся.
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
                  <th>Инфлюенсер-программа</th>
                  <th>Инфлюенсер</th>
                  <th>Админ</th>
                  <th>Сброс пароля</th>
                </tr>
              </thead>
              <tbody>
                {members.length === 0 && (
                  <tr>
                    <td colSpan={13} className="admin-table-empty">
                      Пользователи не найдены.
                    </td>
                  </tr>
                )}

                {members.map((member) => (
                  <React.Fragment key={member.id}>
                    <tr>
                      <td>
                        <div className="admin-member-name-cell">
                          <span>{member.first_name}</span>
                          {member.is_influencer && (
                            <span className="admin-badge admin-badge-influencer">Инфлюенсер</span>
                          )}
                        </div>
                      </td>
                      <td>{member.last_name}</td>
                      <td>{member.phone}</td>
                      <td>{member.email || '—'}</td>
                      <td>{member.is_influencer ? 'Инфлюенсер' : 'Игрок'}</td>
                      <td>{member.is_admin ? 'Админ' : 'Пользователь'}</td>
                      <td>{member.total_referrals}</td>
                      <td>{member.total_bonus_points}</td>
                      <td>{member.total_money_earned} ₽</td>
                      <td>
                        {member.is_influencer ? (
                          <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={() =>
                              handleToggleFlag(member.id, 'is_influencer', false)
                            }
                          >
                            Снять статус инфлюенсера
                          </button>
                        ) : (
                          <button
                            type="button"
                            className="btn btn-primary"
                            onClick={() =>
                              handleToggleFlag(member.id, 'is_influencer', true)
                            }
                          >
                            Сделать инфлюенсером
                          </button>
                        )}
                      </td>
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
                      <td>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          onClick={() => openResetModal(member.id)}
                        >
                          Сбросить пароль
                        </button>
                      </td>
                    </tr>

                    {resetModalMemberId === member.id && (
                      <tr>
                        <td colSpan={13} className="admin-reset-row">
                          <div className="admin-reset-panel">
                            <h4 className="admin-reset-title">
                              Сброс пароля для пользователя ID {member.id}
                            </h4>
                            <p className="admin-reset-text">
                              Вы можете задать новый пароль вручную или оставить поле пустым,
                              чтобы система сгенерировала случайный безопасный пароль.
                            </p>

                            <div className="admin-form-row">
                              <label className="admin-form-label" htmlFor={`resetPassword-${member.id}`}>
                                Новый пароль (необязательно)
                              </label>
                              <input
                                id={`resetPassword-${member.id}`}
                                type="password"
                                className="admin-form-input"
                                value={resetCustomPassword}
                                onChange={(event) => setResetCustomPassword(event.target.value)}
                                placeholder="Оставьте пустым для автогенерации пароля"
                              />
                            </div>

                            {resetError && (
                              <div className="admin-form-error">{resetError}</div>
                            )}

                            {resetSuccess && (
                              <div className="admin-form-success">{resetSuccess}</div>
                            )}

                            {resetResultPassword && (
                              <div className="admin-reset-password-result">
                                <div className="admin-reset-password-label">
                                  Сгенерированный пароль (показывается один раз):
                                </div>
                                <div className="admin-reset-password-value">
                                  {resetResultPassword}
                                </div>
                                <div className="admin-reset-password-note">
                                  Передайте этот пароль пользователю безопасным способом.
                                </div>
                              </div>
                            )}

                            <div className="admin-reset-actions">
                              <button
                                type="button"
                                className="btn btn-secondary"
                                onClick={closeResetModal}
                                disabled={resetLoading}
                              >
                                Отмена
                              </button>
                              <button
                                type="button"
                                className="btn btn-primary"
                                onClick={handleConfirmReset}
                                disabled={resetLoading}
                              >
                                {resetLoading ? 'Сброс...' : 'Сбросить пароль'}
                              </button>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
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
