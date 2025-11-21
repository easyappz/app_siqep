import React, { useEffect, useState } from 'react';
import {
  getAdminMembers,
  getAdminMemberDetail,
  adjustAdminMemberBalance,
} from '../../api/admin';

const formatMoney = (value) => {
  if (value === null || value === undefined) {
    return '0.00';
  }

  const numberValue = Number(value);
  if (Number.isNaN(numberValue)) {
    return String(value);
  }

  return numberValue.toFixed(2);
};

const formatVCoins = (value) => {
  if (value === null || value === undefined) {
    return '0.00';
  }

  const numberValue = Number(value);
  if (Number.isNaN(numberValue)) {
    return String(value);
  }

  return numberValue.toFixed(2);
};

const formatDateTime = (isoString) => {
  if (!isoString) {
    return '—';
  }

  try {
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) {
      return isoString;
    }
    return date.toLocaleString('ru-RU');
  } catch (error) {
    return isoString;
  }
};

const formatDelta = (value) => {
  if (value === null || value === undefined) {
    return '—';
  }

  const numberValue = Number(value);
  if (Number.isNaN(numberValue)) {
    return String(value);
  }

  if (numberValue > 0) {
    return `+${numberValue}`;
  }

  if (numberValue < 0) {
    return `${numberValue}`;
  }

  return '0';
};

const getOperationTypeLabel = (type) => {
  if (type === 'deposit_accrual') {
    return 'Начисление депозита';
  }
  if (type === 'deposit_withdrawal') {
    return 'Списание депозита';
  }
  if (type === 'vcoins_increase') {
    return 'Начисление V-Coins';
  }
  if (type === 'vcoins_decrease') {
    return 'Списание V-Coins';
  }
  if (type === 'combined_adjustment') {
    return 'Комбинированная корректировка';
  }
  if (!type) {
    return 'Операция';
  }
  return 'Другая операция';
};

const AdminUsersPage = () => {
  const [members, setMembers] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const [searchPhone, setSearchPhone] = useState('');

  const [loadingList, setLoadingList] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [submittingOperation, setSubmittingOperation] = useState(false);

  const [listError, setListError] = useState('');
  const [detailError, setDetailError] = useState('');
  const [operationError, setOperationError] = useState('');
  const [operationSuccess, setOperationSuccess] = useState('');

  const [selectedMemberId, setSelectedMemberId] = useState(null);
  const [selectedMember, setSelectedMember] = useState(null);

  const [depositDelta, setDepositDelta] = useState('');
  const [vcoinsDelta, setVcoinsDelta] = useState('');
  const [comment, setComment] = useState('');

  const loadMembers = async (pageParam, searchValue) => {
    setLoadingList(true);
    setListError('');

    try {
      const params = {
        page: pageParam,
      };

      if (searchValue) {
        params.search_phone = searchValue;
      }

      const data = await getAdminMembers(params);
      const results = Array.isArray(data.results) ? data.results : [];

      setMembers(results);
      const totalCount = typeof data.count === 'number' ? data.count : results.length;
      setCount(totalCount);

      const pageSize = results.length > 0 ? results.length : 1;
      const pages = totalCount ? Math.max(1, Math.ceil(totalCount / pageSize)) : 1;
      setTotalPages(pages);
    } catch (error) {
      console.error('Failed to load admin members list', error);
      setListError('Не удалось загрузить список пользователей. Пожалуйста, попробуйте позже.');
    } finally {
      setLoadingList(false);
    }
  };

  const loadMemberDetail = async (memberId) => {
    if (!memberId) {
      return;
    }

    setLoadingDetail(true);
    setDetailError('');

    try {
      const data = await getAdminMemberDetail(memberId);
      setSelectedMember(data || null);
    } catch (error) {
      console.error('Failed to load admin member detail', error);
      setDetailError('Не удалось загрузить детали пользователя. Попробуйте позже.');
    } finally {
      setLoadingDetail(false);
    }
  };

  useEffect(() => {
    loadMembers(page, searchPhone);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setPage(1);
      loadMembers(1, searchPhone);
    }, 400);

    return () => {
      window.clearTimeout(timeoutId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchPhone]);

  const handleSelectMember = (memberId) => {
    setSelectedMemberId(memberId);
    setOperationError('');
    setOperationSuccess('');
    setDepositDelta('');
    setVcoinsDelta('');
    setComment('');
    loadMemberDetail(memberId);
  };

  const handleAdjustSubmit = async (event) => {
    event.preventDefault();

    if (!selectedMemberId) {
      setOperationError('Сначала выберите пользователя в списке слева.');
      setOperationSuccess('');
      return;
    }

    const depositTrimmed = depositDelta ? String(depositDelta).trim() : '';
    const vcoinsTrimmed = vcoinsDelta ? String(vcoinsDelta).trim() : '';

    const hasDepositChange = depositTrimmed !== '';
    const hasVcoinsChange = vcoinsTrimmed !== '';

    if (!hasDepositChange && !hasVcoinsChange) {
      setOperationError('Укажите изменение депозита или V-Coins (значения не должны быть пустыми или равными нулю).');
      setOperationSuccess('');
      return;
    }

    const payload = {};

    if (hasDepositChange) {
      const depositNumber = Number(depositTrimmed.replace(',', '.'));
      if (!depositNumber || Number.isNaN(depositNumber)) {
        setOperationError('Введите корректное число для изменения депозита (может быть положительным или отрицательным).');
        setOperationSuccess('');
        return;
      }
      payload.deposit_delta = depositNumber;
    }

    if (hasVcoinsChange) {
      const vcoinsNumber = Number(vcoinsTrimmed.replace(',', '.'));
      if (!vcoinsNumber || Number.isNaN(vcoinsNumber)) {
        setOperationError('Введите корректное число для изменения V-Coins (может быть положительным или отрицательным).');
        setOperationSuccess('');
        return;
      }
      payload.vcoins_delta = vcoinsNumber;
    }

    const commentTrimmed = comment ? String(comment).trim() : '';
    if (commentTrimmed) {
      payload.comment = commentTrimmed;
    }

    setSubmittingOperation(true);
    setOperationError('');
    setOperationSuccess('');

    try {
      const updated = await adjustAdminMemberBalance(selectedMemberId, payload);
      setSelectedMember(updated || null);

      // Обновляем список, чтобы отразить новые балансы в левой колонке
      loadMembers(page, searchPhone);

      setOperationSuccess('Операция успешно выполнена. Балансы обновлены.');
    } catch (error) {
      console.error('Failed to adjust member balance', error);

      let message = 'Не удалось выполнить операцию. Проверьте данные и попробуйте ещё раз.';
      const responseData = error && error.response && error.response.data ? error.response.data : null;

      if (responseData) {
        if (typeof responseData === 'string') {
          message = responseData;
        } else if (responseData.detail && typeof responseData.detail === 'string') {
          message = responseData.detail;
        } else if (responseData.deposit_delta) {
          const value = Array.isArray(responseData.deposit_delta)
            ? responseData.deposit_delta[0]
            : responseData.deposit_delta;
          message = String(value);
        } else if (responseData.vcoins_delta) {
          const value = Array.isArray(responseData.vcoins_delta)
            ? responseData.vcoins_delta[0]
            : responseData.vcoins_delta;
          message = String(value);
        }
      }

      setOperationError(message);
      setOperationSuccess('');
    } finally {
      setSubmittingOperation(false);
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

  const getMemberDepositBalance = (member) => {
    if (!member) {
      return '0.00';
    }

    if (member.wallet_balance !== null && member.wallet_balance !== undefined) {
      return formatMoney(member.wallet_balance);
    }

    if (member.cash_balance !== null && member.cash_balance !== undefined) {
      return formatMoney(member.cash_balance);
    }

    return '0.00';
  };

  const getMemberVcoinsBalance = (member) => {
    if (!member) {
      return '0.00';
    }

    if (member.v_coins_balance !== null && member.v_coins_balance !== undefined) {
      return formatVCoins(member.v_coins_balance);
    }

    return '0.00';
  };

  const isMemberActive = (member) => {
    if (!member) {
      return false;
    }

    if (typeof member.is_active === 'boolean') {
      return member.is_active;
    }

    const deposit = Number(getMemberDepositBalance(member));
    const vcoins = Number(getMemberVcoinsBalance(member));

    return deposit > 0 || vcoins > 0;
  };

  const activeFlag = isMemberActive(selectedMember);
  const selectedDepositBalance = getMemberDepositBalance(selectedMember);
  const selectedVcoinsBalance = getMemberVcoinsBalance(selectedMember);

  return (
    <main
      data-easytag="id1-react/src/components/Admin/Users.jsx"
      className="page-admin-users-inner"
    >
      <section className="card admin-section-header">
        <h2 className="section-title">Пользователи и балансы</h2>
        <p className="section-subtitle">
          Найдите пользователя по номеру телефона, просмотрите его текущие балансы и
          выполните ручное начисление или списание депозита и V-Coins.
        </p>
      </section>

      <section className="card admin-users-layout-card">
        <div className="admin-users-layout">
          {/* Левая колонка: список пользователей */}
          <div className="admin-users-list">
            <div className="admin-users-search">
              <label className="admin-form-label" htmlFor="adminSearchPhone">
                Поиск по номеру телефона
              </label>
              <input
                id="adminSearchPhone"
                type="text"
                className="admin-users-search-input"
                placeholder="Поиск по номеру телефона"
                value={searchPhone}
                onChange={(event) => setSearchPhone(event.target.value)}
              />
              <p className="admin-users-search-hint">
                Введите часть номера телефона, чтобы быстро найти нужного пользователя.
              </p>
            </div>

            {loadingList && (
              <div className="admin-users-list-status">Загрузка списка пользователей...</div>
            )}

            {listError && !loadingList && (
              <div className="admin-table-error admin-users-list-error">{listError}</div>
            )}

            {!loadingList && !listError && (
              <div className="admin-user-list">
                {members.length === 0 ? (
                  <div className="admin-users-list-empty">Пользователи не найдены.</div>
                ) : (
                  members.map((member) => {
                    const fullName = `${member.first_name || ''} ${member.last_name || ''}`.trim();
                    const displayName = fullName || member.phone || `ID ${member.id}`;
                    const active = isMemberActive(member);
                    const isSelected = selectedMemberId === member.id;

                    return (
                      <button
                        type="button"
                        key={member.id}
                        className={
                          isSelected
                            ? 'admin-user-item admin-user-item--active'
                            : 'admin-user-item'
                        }
                        onClick={() => handleSelectMember(member.id)}
                      >
                        <div className="admin-user-item-header">
                          <div className="admin-user-item-name">{displayName}</div>
                          <div
                            className={
                              active
                                ? 'admin-user-status-badge admin-user-status-badge--active'
                                : 'admin-user-status-badge admin-user-status-badge--inactive'
                            }
                          >
                            {active ? 'Активен' : 'Неактивен'}
                          </div>
                        </div>
                        <div className="admin-user-item-subtitle">
                          <span className="admin-user-item-phone">{member.phone || '—'}</span>
                          {member.email && (
                            <span className="admin-user-item-email">{member.email}</span>
                          )}
                        </div>
                        <div className="admin-user-item-balances">
                          <div className="admin-user-item-balance">
                            <span className="admin-user-item-balance-label">Депозит</span>
                            <span className="admin-user-item-balance-value">
                              {getMemberDepositBalance(member)} ₽
                            </span>
                          </div>
                          <div className="admin-user-item-balance">
                            <span className="admin-user-item-balance-label">V-Coins</span>
                            <span className="admin-user-item-balance-value">
                              {getMemberVcoinsBalance(member)}
                            </span>
                          </div>
                        </div>
                      </button>
                    );
                  })
                )}
              </div>
            )}

            <div className="admin-pagination admin-users-pagination">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handlePrevPage}
                disabled={page <= 1 || loadingList}
              >
                Назад
              </button>
              <span className="admin-pagination-info">
                Страница {page} из {totalPages} • Всего: {count}
              </span>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleNextPage}
                disabled={page >= totalPages || loadingList}
              >
                Вперёд
              </button>
            </div>
          </div>

          {/* Правая колонка: подробности и операции */}
          <div className="admin-user-detail">
            {!selectedMember && !loadingDetail && (
              <div className="admin-user-detail-empty">
                Выберите пользователя из списка слева, чтобы увидеть балансы и историю
                операций.
              </div>
            )}

            {loadingDetail && (
              <div className="admin-users-list-status">Загрузка данных пользователя...</div>
            )}

            {detailError && !loadingDetail && (
              <div className="admin-table-error">{detailError}</div>
            )}

            {selectedMember && !loadingDetail && (
              <>
                <section className="admin-user-detail-header-section">
                  <div className="admin-user-header">
                    <div>
                      <h3 className="admin-user-title">
                        {selectedMember.first_name || selectedMember.last_name
                          ? `${selectedMember.first_name || ''} ${selectedMember.last_name || ''}`.trim()
                          : selectedMember.phone || `ID ${selectedMember.id}`}
                      </h3>
                      <p className="admin-user-subtitle">
                        Телефон: {selectedMember.phone || '—'}
                        {selectedMember.email && ` • Email: ${selectedMember.email}`}
                      </p>
                    </div>
                    <div className="admin-user-header-status">
                      <div
                        className={
                          activeFlag
                            ? 'admin-user-status-badge admin-user-status-badge--active'
                            : 'admin-user-status-badge admin-user-status-badge--inactive'
                        }
                      >
                        {activeFlag ? 'Активен' : 'Неактивен'}
                      </div>
                      {selectedMember.is_influencer && (
                        <div className="admin-user-role-badge">Инфлюенсер</div>
                      )}
                      {selectedMember.is_admin && (
                        <div className="admin-user-role-badge admin-user-role-badge--admin">
                          Администратор
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="admin-balances">
                    <h4 className="admin-subsection-title">Текущие балансы</h4>
                    <p className="admin-subsection-caption">
                      Значения после всех операций. Денежный баланс используется как депозит
                      в рублях, V-Coins — виртуальные фишки.
                    </p>

                    <div className="admin-balances-grid">
                      <div className="admin-balance-card">
                        <div className="admin-balance-label">Депозит (рубли)</div>
                        <div className="admin-balance-value">
                          {selectedDepositBalance} ₽
                        </div>
                        <div className="admin-balance-caption">
                          Денежный баланс, который нельзя сделать отрицательным при
                          списаниях.
                        </div>
                      </div>

                      <div className="admin-balance-card">
                        <div className="admin-balance-label">V-Coins</div>
                        <div className="admin-balance-value">
                          {selectedVcoinsBalance}
                        </div>
                        <div className="admin-balance-caption">
                          Виртуальные фишки, начисляемые за активность и рефералов.
                        </div>
                      </div>
                    </div>
                  </div>
                </section>

                <section className="admin-user-operation-section">
                  <h4 className="admin-subsection-title">Ручная корректировка балансов</h4>
                  <p className="admin-subsection-caption">
                    Положительные числа начисляют средства или V-Coins, отрицательные —
                    списывают. Система не позволит сделать депозиты или V-Coins отрицательными.
                  </p>

                  <form className="admin-user-operation-form" onSubmit={handleAdjustSubmit}>
                    <div className="admin-form-grid admin-user-operation-grid">
                      <div className="admin-form-row">
                        <label
                          className="admin-form-label"
                          htmlFor="depositDeltaInput"
                        >
                          Изменение депозита (₽)
                        </label>
                        <input
                          id="depositDeltaInput"
                          type="number"
                          step="0.01"
                          className="admin-form-input"
                          value={depositDelta}
                          onChange={(event) => setDepositDelta(event.target.value)}
                          placeholder="Например: 500 или -300"
                        />
                      </div>

                      <div className="admin-form-row">
                        <label
                          className="admin-form-label"
                          htmlFor="vcoinsDeltaInput"
                        >
                          Изменение V-Coins
                        </label>
                        <input
                          id="vcoinsDeltaInput"
                          type="number"
                          step="1"
                          className="admin-form-input"
                          value={vcoinsDelta}
                          onChange={(event) => setVcoinsDelta(event.target.value)}
                          placeholder="Например: 1000 или -500"
                        />
                      </div>

                      <div className="admin-form-row admin-user-comment-row">
                        <label
                          className="admin-form-label"
                          htmlFor="adminOperationComment"
                        >
                          Комментарий
                        </label>
                        <textarea
                          id="adminOperationComment"
                          className="admin-form-input admin-form-textarea"
                          rows={2}
                          value={comment}
                          onChange={(event) => setComment(event.target.value)}
                          placeholder="Например: корректировка по итогам проверки или бонусное начисление"
                        />
                      </div>

                      {operationError && (
                        <p className="admin-form-error admin-operation-message">
                          {operationError}
                        </p>
                      )}

                      {operationSuccess && (
                        <p className="admin-form-success admin-operation-message">
                          {operationSuccess}
                        </p>
                      )}

                      <div className="admin-form-actions admin-user-operation-actions">
                        <button
                          type="submit"
                          className="btn btn-primary"
                          disabled={submittingOperation}
                        >
                          {submittingOperation
                            ? 'Применение...'
                            : 'Применить операцию'}
                        </button>
                      </div>
                    </div>
                  </form>
                </section>

                <section className="admin-user-history-section">
                  <h4 className="admin-subsection-title">История операций</h4>
                  <p className="admin-subsection-caption">
                    Последние операции по корректировке балансов этого пользователя, в
                    порядке от новых к старым.
                  </p>

                  {!selectedMember.operations || selectedMember.operations.length === 0 ? (
                    <div className="admin-users-list-empty">Операций пока нет.</div>
                  ) : (
                    <div className="admin-history-table-wrapper">
                      <table className="admin-history-table">
                        <thead>
                          <tr>
                            <th>Дата</th>
                            <th>Тип</th>
                            <th>Изменение депозита</th>
                            <th>Изменение V-Coins</th>
                            <th>Баланс депозита</th>
                            <th>Баланс V-Coins</th>
                            <th>Комментарий</th>
                          </tr>
                        </thead>
                        <tbody>
                          {selectedMember.operations.map((operation) => {
                            const key = operation.id || `${operation.created_at || ''}-${operation.operation_type || ''}`;

                            return (
                              <tr key={key}>
                                <td>{formatDateTime(operation.created_at)}</td>
                                <td>{getOperationTypeLabel(operation.operation_type)}</td>
                                <td>{formatDelta(operation.deposit_change)}</td>
                                <td>{formatDelta(operation.vcoins_change)}</td>
                                <td>{formatMoney(operation.balance_deposit_after)}</td>
                                <td>{formatVCoins(operation.balance_vcoins_after)}</td>
                                <td>{operation.comment || '—'}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </section>
              </>
            )}
          </div>
        </div>
      </section>
    </main>
  );
};

export default AdminUsersPage;
