import React, { useEffect, useState } from 'react';
import { fetchAdminMembers, adminDebitWallet } from '../../api/admin';

const AdminWalletPage = () => {
  const [members, setMembers] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [activeMemberId, setActiveMemberId] = useState(null);
  const [debitAmount, setDebitAmount] = useState('');
  const [debitReason, setDebitReason] = useState('');
  const [debitLoading, setDebitLoading] = useState(false);
  const [debitError, setDebitError] = useState('');
  const [debitSuccess, setDebitSuccess] = useState('');

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
      console.error('Failed to load admin members for wallet page', err);
      setError('Не удалось загрузить пользователей. Пожалуйста, попробуйте позже.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMembers(page);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

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

  const openDebitForm = (memberId) => {
    setActiveMemberId(memberId);
    setDebitAmount('');
    setDebitReason('');
    setDebitError('');
    setDebitSuccess('');
  };

  const closeDebitForm = () => {
    setActiveMemberId(null);
    setDebitAmount('');
    setDebitReason('');
    setDebitError('');
    setDebitSuccess('');
  };

  const handleDebitSubmit = async (event) => {
    event.preventDefault();

    if (!activeMemberId) {
      return;
    }

    const trimmedAmount = debitAmount ? String(debitAmount).trim() : '';

    if (!trimmedAmount) {
      setDebitError('Введите сумму для списания.');
      setDebitSuccess('');
      return;
    }

    const numericAmount = Number(trimmedAmount.replace(',', '.'));

    if (!numericAmount || numericAmount <= 0) {
      setDebitError('Сумма списания должна быть положительным числом.');
      setDebitSuccess('');
      return;
    }

    setDebitLoading(true);
    setDebitError('');
    setDebitSuccess('');

    try {
      const payload = {
        member_id: activeMemberId,
        amount: trimmedAmount,
        reason: debitReason || null,
      };

      const tx = await adminDebitWallet(payload);

      const balanceAfter = tx && tx.balance_after ? String(tx.balance_after) : null;

      if (balanceAfter !== null) {
        setMembers((prev) =>
          prev.map((member) =>
            member.id === activeMemberId
              ? {
                  ...member,
                  wallet_balance: balanceAfter,
                  cash_balance: balanceAfter,
                }
              : member
          )
        );
      }

      const successText = balanceAfter
        ? `Средства успешно списаны. Новый баланс: ${balanceAfter} ₽.`
        : 'Средства успешно списаны.';

      setDebitSuccess(successText);
      setDebitError('');
    } catch (err) {
      console.error('Failed to debit wallet by admin', err);

      const responseData = err && err.response && err.response.data ? err.response.data : null;
      let message = 'Не удалось списать средства. Попробуйте ещё раз.';

      if (responseData) {
        if (responseData.amount) {
          const value = Array.isArray(responseData.amount)
            ? responseData.amount[0]
            : responseData.amount;
          message = String(value);
        } else if (responseData.member_id) {
          const value = Array.isArray(responseData.member_id)
            ? responseData.member_id[0]
            : responseData.member_id;
          message = String(value);
        } else if (typeof responseData.detail === 'string') {
          message = responseData.detail;
        }
      }

      setDebitError(message);
      setDebitSuccess('');
    } finally {
      setDebitLoading(false);
    }
  };

  const renderBalance = (member) => {
    if (!member) {
      return '—';
    }

    const rawWallet = member.wallet_balance;
    const rawCash = member.cash_balance;

    if (rawWallet !== null && rawWallet !== undefined && rawWallet !== '') {
      return `${rawWallet} ₽`;
    }

    if (rawCash !== null && rawCash !== undefined && rawCash !== '') {
      return `${rawCash} ₽`;
    }

    return '—';
  };

  return (
    <main
      data-easytag="id1-react/src/components/Admin/Wallet.jsx"
      className="page-admin-users-inner"
    >
      <section className="card admin-section-header">
        <h2 className="section-title">Баланс пользователей</h2>
        <p className="section-subtitle">
          Просмотр кошельков пользователей и ручное списание средств администратором.
        </p>
      </section>

      <section className="card admin-table-card">
        <div className="admin-table-header">
          <div>
            <h3 className="admin-table-title">Список пользователей</h3>
            <p className="admin-table-subtitle">Всего пользователей: {count}</p>
            <p className="admin-table-helper">
              При ручном списании учитывается текущий баланс кошелька пользователя. Если
              средств недостаточно, операция будет отклонена сервером.
            </p>
          </div>
        </div>

        {loading && (
          <p className="admin-table-loading">Загрузка списка пользователей...</p>
        )}

        {error && !loading && <p className="admin-table-error">{error}</p>}

        {!loading && !error && (
          <div className="table-wrapper">
            <table className="table admin-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Имя</th>
                  <th>Фамилия</th>
                  <th>Телефон</th>
                  <th>Email</th>
                  <th>Баланс кошелька</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {members.length === 0 && (
                  <tr>
                    <td colSpan={7} className="admin-table-empty">
                      Пользователи не найдены.
                    </td>
                  </tr>
                )}

                {members.map((member) => (
                  <React.Fragment key={member.id}>
                    <tr>
                      <td>{member.id}</td>
                      <td>{member.first_name}</td>
                      <td>{member.last_name}</td>
                      <td>{member.phone}</td>
                      <td>{member.email || '—'}</td>
                      <td>{renderBalance(member)}</td>
                      <td>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          onClick={() => openDebitForm(member.id)}
                        >
                          Списать средства
                        </button>
                      </td>
                    </tr>

                    {activeMemberId === member.id && (
                      <tr>
                        <td colSpan={7} className="admin-reset-row">
                          <form
                            className="admin-reset-panel admin-form-grid"
                            onSubmit={handleDebitSubmit}
                          >
                            <div className="admin-form-row">
                              <label className="admin-form-label" htmlFor={`debitAmount-${member.id}`}>
                                Сумма списания
                              </label>
                              <input
                                id={`debitAmount-${member.id}`}
                                type="number"
                                step="0.01"
                                min="0"
                                className="admin-form-input"
                                value={debitAmount}
                                onChange={(event) => setDebitAmount(event.target.value)}
                                placeholder="Введите сумму в рублях"
                              />
                            </div>

                            <div className="admin-form-row">
                              <label className="admin-form-label" htmlFor={`debitReason-${member.id}`}>
                                Причина (необязательно)
                              </label>
                              <input
                                id={`debitReason-${member.id}`}
                                type="text"
                                className="admin-form-input"
                                value={debitReason}
                                onChange={(event) => setDebitReason(event.target.value)}
                                placeholder="Комментарий для истории операций"
                              />
                            </div>

                            {debitError && (
                              <p className="admin-form-error">{debitError}</p>
                            )}

                            {debitSuccess && (
                              <p className="admin-form-success">{debitSuccess}</p>
                            )}

                            <div className="admin-form-actions">
                              <button
                                type="button"
                                className="btn btn-secondary"
                                onClick={closeDebitForm}
                                disabled={debitLoading}
                              >
                                Отмена
                              </button>
                              <button
                                type="submit"
                                className="btn btn-primary"
                                disabled={debitLoading}
                              >
                                {debitLoading ? 'Списание...' : 'Списать средства'}
                              </button>
                            </div>
                          </form>
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

export default AdminWalletPage;
