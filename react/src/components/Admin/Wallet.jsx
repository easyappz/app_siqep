import React, { useEffect, useState } from 'react';
import {
  fetchAdminMembers,
  adminDebitWallet,
  adminDepositWallet,
  adminSpendWallet,
} from '../../api/admin';

const AdminWalletPage = () => {
  const [members, setMembers] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [activeMemberId, setActiveMemberId] = useState(null);

  const [depositAmount, setDepositAmount] = useState('');
  const [depositReason, setDepositReason] = useState('');
  const [depositLoading, setDepositLoading] = useState(false);
  const [depositError, setDepositError] = useState('');
  const [depositSuccess, setDepositSuccess] = useState('');

  const [spendAmount, setSpendAmount] = useState('');
  const [spendDescription, setSpendDescription] = useState('');
  const [spendCategory, setSpendCategory] = useState('');
  const [spendLoading, setSpendLoading] = useState(false);
  const [spendError, setSpendError] = useState('');
  const [spendSuccess, setSpendSuccess] = useState('');

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

  const resetAllOperationState = () => {
    setDepositAmount('');
    setDepositReason('');
    setDepositError('');
    setDepositSuccess('');

    setSpendAmount('');
    setSpendDescription('');
    setSpendCategory('');
    setSpendError('');
    setSpendSuccess('');

    setDebitAmount('');
    setDebitReason('');
    setDebitError('');
    setDebitSuccess('');
  };

  const openOperationsPanel = (memberId) => {
    setActiveMemberId(memberId);
    resetAllOperationState();
  };

  const closeOperationsPanel = () => {
    setActiveMemberId(null);
    resetAllOperationState();
  };

  const updateMemberBalanceFromTransaction = (memberId, tx) => {
    if (!tx) {
      return;
    }

    const balanceAfter =
      typeof tx.balance_after === 'number' || typeof tx.balance_after === 'string'
        ? String(tx.balance_after)
        : null;

    if (balanceAfter === null) {
      return;
    }

    setMembers((prev) =>
      prev.map((member) =>
        member.id === memberId
          ? {
              ...member,
              wallet_balance: balanceAfter,
              cash_balance: balanceAfter,
            }
          : member,
      ),
    );
  };

  const parsePositiveAmount = (raw) => {
    const trimmed = raw ? String(raw).trim() : '';
    if (!trimmed) {
      return { valid: false, value: null };
    }
    const normalized = trimmed.replace(',', '.');
    const numeric = Number(normalized);
    if (!numeric || Number.isNaN(numeric) || numeric <= 0) {
      return { valid: false, value: null };
    }
    return { valid: true, value: normalized };
  };

  const extractErrorMessage = (error, defaultMessage) => {
    const responseData = error && error.response && error.response.data ? error.response.data : null;
    if (!responseData) {
      return defaultMessage;
    }

    if (responseData.amount) {
      const value = Array.isArray(responseData.amount)
        ? responseData.amount[0]
        : responseData.amount;
      return String(value);
    }
    if (responseData.member_id) {
      const value = Array.isArray(responseData.member_id)
        ? responseData.member_id[0]
        : responseData.member_id;
      return String(value);
    }
    if (typeof responseData.detail === 'string') {
      return responseData.detail;
    }
    if (typeof responseData.error === 'string') {
      return responseData.error;
    }
    if (
      Array.isArray(responseData.non_field_errors) &&
      responseData.non_field_errors.length > 0 &&
      typeof responseData.non_field_errors[0] === 'string'
    ) {
      return responseData.non_field_errors[0];
    }

    return defaultMessage;
  };

  const handleDepositSubmit = async (event) => {
    event.preventDefault();

    if (!activeMemberId) {
      return;
    }

    setDepositError('');
    setDepositSuccess('');

    const parsed = parsePositiveAmount(depositAmount);
    if (!parsed.valid) {
      setDepositError('Сумма пополнения должна быть положительным числом.');
      return;
    }

    setDepositLoading(true);

    try {
      const payload = {
        member_id: activeMemberId,
        amount: parsed.value,
        reason: depositReason || null,
      };

      const tx = await adminDepositWallet(payload);

      updateMemberBalanceFromTransaction(activeMemberId, tx);

      const balanceAfter =
        tx && (typeof tx.balance_after === 'number' || typeof tx.balance_after === 'string')
          ? String(tx.balance_after)
          : '';

      const successText = balanceAfter
        ? `Пополнение выполнено. Новый баланс: ${balanceAfter} ₽.`
        : 'Пополнение выполнено.';

      setDepositSuccess(successText);
      setDepositError('');
    } catch (err) {
      console.error('Failed to deposit to wallet by admin', err);
      const message = extractErrorMessage(
        err,
        'Не удалось пополнить кошелёк. Попробуйте ещё раз.',
      );
      setDepositError(message);
      setDepositSuccess('');
    } finally {
      setDepositLoading(false);
    }
  };

  const handleSpendSubmit = async (event) => {
    event.preventDefault();

    if (!activeMemberId) {
      return;
    }

    setSpendError('');
    setSpendSuccess('');

    const parsed = parsePositiveAmount(spendAmount);
    if (!parsed.valid) {
      setSpendError('Сумма списания должна быть положительным числом.');
      return;
    }

    if (!spendDescription || !spendDescription.trim()) {
      setSpendError('Укажите описание операции (например, за какой турнир списание).');
      return;
    }

    setSpendLoading(true);

    try {
      const payload = {
        member_id: activeMemberId,
        amount: parsed.value,
        description: spendDescription,
      };

      if (spendCategory && spendCategory.trim()) {
        payload.category = spendCategory.trim();
      }

      const tx = await adminSpendWallet(payload);

      updateMemberBalanceFromTransaction(activeMemberId, tx);

      const balanceAfter =
        tx && (typeof tx.balance_after === 'number' || typeof tx.balance_after === 'string')
          ? String(tx.balance_after)
          : '';

      const successText = balanceAfter
        ? `Списание как игра выполнено. Новый баланс: ${balanceAfter} ₽.`
        : 'Списание как игра выполнено.';

      setSpendSuccess(successText);
      setSpendError('');
    } catch (err) {
      console.error('Failed to spend from wallet by admin', err);

      const responseData = err && err.response && err.response.data ? err.response.data : null;
      let message = 'Не удалось выполнить списание. Попробуйте ещё раз.';

      if (responseData) {
        if (responseData.amount) {
          const value = Array.isArray(responseData.amount)
            ? responseData.amount[0]
            : responseData.amount;
          message = String(value);
        } else if (typeof responseData.detail === 'string') {
          message = responseData.detail;
        } else if (typeof responseData.error === 'string') {
          message = responseData.error;
        }

        const textToCheck = JSON.stringify(responseData).toLowerCase();
        if (
          textToCheck.includes('insufficient') ||
          textToCheck.includes('недостаточно')
        ) {
          message = 'Недостаточно средств на кошельке пользователя.';
        }
      }

      setSpendError(message);
      setSpendSuccess('');
    } finally {
      setSpendLoading(false);
    }
  };

  const handleDebitSubmit = async (event) => {
    event.preventDefault();

    if (!activeMemberId) {
      return;
    }

    setDebitError('');
    setDebitSuccess('');

    const parsed = parsePositiveAmount(debitAmount);
    if (!parsed.valid) {
      setDebitError('Сумма списания должна быть положительным числом.');
      return;
    }

    setDebitLoading(true);

    try {
      const payload = {
        member_id: activeMemberId,
        amount: parsed.value,
        reason: debitReason || null,
      };

      const tx = await adminDebitWallet(payload);

      updateMemberBalanceFromTransaction(activeMemberId, tx);

      const balanceAfter =
        tx && (typeof tx.balance_after === 'number' || typeof tx.balance_after === 'string')
          ? String(tx.balance_after)
          : '';

      const successText = balanceAfter
        ? `Административное списание выполнено. Новый баланс: ${balanceAfter} ₽.`
        : 'Административное списание выполнено.';

      setDebitSuccess(successText);
      setDebitError('');
    } catch (err) {
      console.error('Failed to debit wallet by admin', err);
      const message = extractErrorMessage(
        err,
        'Не удалось выполнить административное списание. Попробуйте ещё раз.',
      );
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
          Просмотр кошельков пользователей и ручные операции с балансом: пополнение,
          списание как игровая трата и административные корректировки.
        </p>
      </section>

      <section className="card admin-table-card">
        <div className="admin-table-header">
          <div>
            <h3 className="admin-table-title">Список пользователей</h3>
            <p className="admin-table-subtitle">Всего пользователей: {count}</p>
            <p className="admin-table-helper">
              Пополнение и списание как игра участвуют в стандартной логике кошелька и
              реферальных бонусов. Административное списание предназначено только для
              ручных корректировок и не влияет на реферальные начисления.
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
                          onClick={() => openOperationsPanel(member.id)}
                        >
                          Операции с балансом
                        </button>
                      </td>
                    </tr>

                    {activeMemberId === member.id && (
                      <tr>
                        <td colSpan={7} className="admin-reset-row">
                          <div className="admin-reset-panel admin-form-grid admin-wallet-operations-panel">
                            <div className="admin-wallet-operation-column">
                              <h4 className="admin-form-title">Пополнение кошелька</h4>
                              <p className="admin-form-subtitle">
                                Пополнение баланса пользователя в рублях. Используется для
                                ручного начисления средств.
                              </p>
                              <form onSubmit={handleDepositSubmit}>
                                <div className="admin-form-row">
                                  <label
                                    className="admin-form-label"
                                    htmlFor={`depositAmount-${member.id}`}
                                  >
                                    Сумма пополнения
                                  </label>
                                  <input
                                    id={`depositAmount-${member.id}`}
                                    type="number"
                                    step="0.01"
                                    min="0"
                                    className="admin-form-input"
                                    value={depositAmount}
                                    onChange={(event) => setDepositAmount(event.target.value)}
                                    placeholder="Введите сумму в рублях"
                                  />
                                </div>

                                <div className="admin-form-row">
                                  <label
                                    className="admin-form-label"
                                    htmlFor={`depositReason-${member.id}`}
                                  >
                                    Комментарий (необязательно)
                                  </label>
                                  <input
                                    id={`depositReason-${member.id}`}
                                    type="text"
                                    className="admin-form-input"
                                    value={depositReason}
                                    onChange={(event) => setDepositReason(event.target.value)}
                                    placeholder="Например: бонусное начисление"
                                  />
                                </div>

                                {depositError && (
                                  <p className="admin-form-error">{depositError}</p>
                                )}

                                {depositSuccess && (
                                  <p className="admin-form-success">{depositSuccess}</p>
                                )}

                                <div className="admin-form-actions">
                                  <button
                                    type="submit"
                                    className="btn btn-primary"
                                    disabled={depositLoading}
                                  >
                                    {depositLoading ? 'Пополнение...' : 'Пополнить'}
                                  </button>
                                </div>
                              </form>
                            </div>

                            <div className="admin-wallet-operation-column">
                              <h4 className="admin-form-title">Списание как игра/трата</h4>
                              <p className="admin-form-subtitle">
                                Моделирует обычную трату игрока (турнир, сервис и т.п.). Такое
                                списание участвует в реферальной логике и может создавать
                                бонусы для рефереров.
                              </p>
                              <form onSubmit={handleSpendSubmit}>
                                <div className="admin-form-row">
                                  <label
                                    className="admin-form-label"
                                    htmlFor={`spendAmount-${member.id}`}
                                  >
                                    Сумма списания
                                  </label>
                                  <input
                                    id={`spendAmount-${member.id}`}
                                    type="number"
                                    step="0.01"
                                    min="0"
                                    className="admin-form-input"
                                    value={spendAmount}
                                    onChange={(event) => setSpendAmount(event.target.value)}
                                    placeholder="Введите сумму в рублях"
                                  />
                                </div>

                                <div className="admin-form-row">
                                  <label
                                    className="admin-form-label"
                                    htmlFor={`spendDescription-${member.id}`}
                                  >
                                    Описание операции
                                  </label>
                                  <input
                                    id={`spendDescription-${member.id}`}
                                    type="text"
                                    className="admin-form-input"
                                    value={spendDescription}
                                    onChange={(event) =>
                                      setSpendDescription(event.target.value)
                                    }
                                    placeholder="Например: турнир, рейк, сервис"
                                  />
                                </div>

                                <div className="admin-form-row">
                                  <label
                                    className="admin-form-label"
                                    htmlFor={`spendCategory-${member.id}`}
                                  >
                                    Категория (необязательно)
                                  </label>
                                  <input
                                    id={`spendCategory-${member.id}`}
                                    type="text"
                                    className="admin-form-input"
                                    value={spendCategory}
                                    onChange={(event) => setSpendCategory(event.target.value)}
                                    placeholder="Например: игра, сервис"
                                  />
                                </div>

                                {spendError && (
                                  <p className="admin-form-error">{spendError}</p>
                                )}

                                {spendSuccess && (
                                  <p className="admin-form-success">{spendSuccess}</p>
                                )}

                                <div className="admin-form-actions">
                                  <button
                                    type="submit"
                                    className="btn btn-secondary"
                                    disabled={spendLoading}
                                  >
                                    {spendLoading ? 'Списание...' : 'Списать как игру'}
                                  </button>
                                </div>
                              </form>
                            </div>

                            <div className="admin-wallet-operation-column admin-wallet-operation-column-narrow">
                              <h4 className="admin-form-title">Административное списание</h4>
                              <p className="admin-form-subtitle">
                                Используется для исправления ошибок и технических корректировок.
                                Не участвует в реферальной логике.
                              </p>
                              <form onSubmit={handleDebitSubmit}>
                                <div className="admin-form-row">
                                  <label
                                    className="admin-form-label"
                                    htmlFor={`debitAmount-${member.id}`}
                                  >
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
                                  <label
                                    className="admin-form-label"
                                    htmlFor={`debitReason-${member.id}`}
                                  >
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

                                <div className="admin-form-actions admin-form-actions-row">
                                  <button
                                    type="button"
                                    className="btn btn-outline"
                                    onClick={closeOperationsPanel}
                                    disabled={debitLoading || spendLoading || depositLoading}
                                  >
                                    Закрыть
                                  </button>
                                  <button
                                    type="submit"
                                    className="btn btn-danger"
                                    disabled={debitLoading}
                                  >
                                    {debitLoading ? 'Списание...' : 'Адм. списание'}
                                  </button>
                                </div>
                              </form>
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

export default AdminWalletPage;
