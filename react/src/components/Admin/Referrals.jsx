import React, { useEffect, useState } from 'react';
import {
  fetchAdminReferrals,
  createAdminReferralEvent,
  fetchAdminMembers,
} from '../../api/admin';
import { fetchReferralTree, fetchReferralRewards } from '../../api/referrals';
import { useAuth } from '../../context/AuthContext';

function getUserTypeLabel(userType) {
  if (userType === 'influencer') {
    return 'Инфлюенсер';
  }
  return 'Игрок';
}

function getRankLabel(rank) {
  if (rank === 'silver') {
    return 'Серебряный';
  }
  if (rank === 'gold') {
    return 'Золотой';
  }
  if (rank === 'platinum') {
    return 'Платиновый';
  }
  return 'Стандарт';
}

const AdminReferralsPage = () => {
  const { member } = useAuth();

  const [referrals, setReferrals] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [typeFilter, setTypeFilter] = useState('all');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');

  const [createReferredId, setCreateReferredId] = useState('');
  const [createDepositAmount, setCreateDepositAmount] = useState('1000');
  const [createDateTime, setCreateDateTime] = useState('');
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState('');
  const [createSuccess, setCreateSuccess] = useState('');

  const [memberSearchQuery, setMemberSearchQuery] = useState('');
  const [memberSearchResults, setMemberSearchResults] = useState([]);
  const [memberSearchLoading, setMemberSearchLoading] = useState(false);
  const [memberSearchError, setMemberSearchError] = useState('');
  const [selectedMemberId, setSelectedMemberId] = useState('');
  const [selectedMember, setSelectedMember] = useState(null);

  const [memberTreeData, setMemberTreeData] = useState([]);
  const [memberTreeLoading, setMemberTreeLoading] = useState(false);
  const [memberTreeError, setMemberTreeError] = useState('');

  const [memberRewardsData, setMemberRewardsData] = useState(null);
  const [memberRewardsLoading, setMemberRewardsLoading] = useState(false);
  const [memberRewardsError, setMemberRewardsError] = useState('');

  const loadReferrals = async (pageParam, options) => {
    setLoading(true);
    setError('');

    try {
      const params = { page: pageParam };

      if (options && options.typeFilter) {
        if (options.typeFilter === 'influencers') {
          params.is_influencer = true;
        }
        if (options.typeFilter === 'regular') {
          params.is_influencer = false;
        }
      }

      if (options && options.fromDate) {
        params.from_date = options.fromDate;
      }

      if (options && options.toDate) {
        params.to_date = options.toDate;
      }

      const data = await fetchAdminReferrals(params);
      const results = Array.isArray(data.results) ? data.results : [];

      setReferrals(results);
      setCount(typeof data.count === 'number' ? data.count : results.length);

      const pageSize = results.length > 0 ? results.length : 1;
      const pages = data.count ? Math.max(1, Math.ceil(data.count / pageSize)) : 1;
      setTotalPages(pages);
    } catch (err) {
      console.error('Failed to load admin referrals', err);
      setError('Не удалось загрузить реферальные события. Пожалуйста, попробуйте позже.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReferrals(page, { typeFilter, fromDate, toDate });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, typeFilter, fromDate, toDate]);

  const handleTypeFilterChange = (event) => {
    setPage(1);
    setTypeFilter(event.target.value);
  };

  const handleFromDateChange = (event) => {
    setPage(1);
    setFromDate(event.target.value);
  };

  const handleToDateChange = (event) => {
    setPage(1);
    setToDate(event.target.value);
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

  const handleCreateReferralEvent = async (event) => {
    event.preventDefault();

    setCreateError('');
    setCreateSuccess('');

    const referredIdNumber = Number(createReferredId);
    const depositAmountNumber = Number(createDepositAmount);

    if (!createReferredId || Number.isNaN(referredIdNumber) || referredIdNumber <= 0) {
      setCreateError('Укажите корректный ID реферала (положительное число).');
      return;
    }

    if (!createDepositAmount || Number.isNaN(depositAmountNumber) || depositAmountNumber <= 0) {
      setCreateError('Укажите корректную сумму депозита (положительное число).');
      return;
    }

    const payload = {
      referred_id: referredIdNumber,
      deposit_amount: depositAmountNumber,
    };

    if (createDateTime) {
      try {
        const createdAtIso = new Date(createDateTime).toISOString();
        if (createdAtIso && createdAtIso !== 'Invalid Date') {
          payload.created_at = createdAtIso;
        }
      } catch (dateError) {
        // ignore invalid date
      }
    }

    setCreateLoading(true);

    try {
      await createAdminReferralEvent(payload);

      setCreateSuccess('Реферальное событие успешно создано.');
      setCreateDepositAmount('1000');
      setCreateDateTime('');

      await loadReferrals(page, { typeFilter, fromDate, toDate });
    } catch (err) {
      console.error('Failed to create admin referral event', err);

      let message =
        'Не удалось создать реферальное событие. Проверьте данные и попробуйте снова.';

      if (err && err.response && err.response.data) {
        const serverData = err.response.data;

        if (typeof serverData === 'string') {
          message = `Ошибка сервера: ${serverData}`;
        } else if (serverData.detail && typeof serverData.detail === 'string') {
          message = `Ошибка: ${serverData.detail}`;
        } else if (
          serverData.non_field_errors &&
          Array.isArray(serverData.non_field_errors) &&
          serverData.non_field_errors.length > 0 &&
          typeof serverData.non_field_errors[0] === 'string'
        ) {
          message = `Ошибка: ${serverData.non_field_errors[0]}`;
        }
      }

      setCreateError(message);
    } finally {
      setCreateLoading(false);
    }
  };

  const formatDateTime = (isoValue) => {
    if (!isoValue) {
      return '';
    }

    try {
      const date = new Date(isoValue);
      return date.toLocaleString('ru-RU');
    } catch (error) {
      return isoValue;
    }
  };

  const handleMemberSearchSubmit = async (event) => {
    event.preventDefault();

    setMemberSearchError('');
    setMemberSearchResults([]);
    setSelectedMemberId('');
    setSelectedMember(null);
    setMemberTreeData([]);
    setMemberTreeError('');
    setMemberRewardsData(null);
    setMemberRewardsError('');

    if (!memberSearchQuery) {
      setMemberSearchError('Введите запрос для поиска пользователя (имя, телефон или ID).');
      return;
    }

    setMemberSearchLoading(true);

    try {
      const data = await fetchAdminMembers({ search: memberSearchQuery, page: 1 });
      const results = Array.isArray(data?.results) ? data.results : [];
      setMemberSearchResults(results);

      if (!results.length) {
        setMemberSearchError('Пользователи не найдены. Измените параметры поиска.');
      }
    } catch (err) {
      console.error('Failed to search admin members', err);
      setMemberSearchError('Не удалось загрузить список пользователей. Попробуйте позже.');
    } finally {
      setMemberSearchLoading(false);
    }
  };

  const loadMemberTree = async (memberId) => {
    if (!memberId) {
      return;
    }

    setMemberTreeLoading(true);
    setMemberTreeError('');

    try {
      const data = await fetchReferralTree({ member_id: memberId });
      const nodes = Array.isArray(data?.nodes)
        ? data.nodes
        : Array.isArray(data)
        ? data
        : [];
      setMemberTreeData(nodes);
    } catch (err) {
      console.error('Failed to load member referral tree', err);
      setMemberTreeError('Не удалось загрузить структуру рефералов пользователя.');
    } finally {
      setMemberTreeLoading(false);
    }
  };

  const loadMemberRewards = async (memberId) => {
    if (!memberId) {
      return;
    }

    setMemberRewardsLoading(true);
    setMemberRewardsError('');

    try {
      const data = await fetchReferralRewards({ member_id: memberId });
      setMemberRewardsData(data || null);
    } catch (err) {
      console.error('Failed to load member referral rewards', err);
      setMemberRewardsError('Не удалось загрузить вознаграждения пользователя.');
    } finally {
      setMemberRewardsLoading(false);
    }
  };

  const handleSelectedMemberChange = (event) => {
    const value = event.target.value;
    setSelectedMemberId(value);

    const found = memberSearchResults.find((item) => String(item.id) === value);
    setSelectedMember(found || null);

    setMemberTreeData([]);
    setMemberTreeError('');
    setMemberRewardsData(null);
    setMemberRewardsError('');

    if (found) {
      setCreateReferredId(String(found.id));
      loadMemberTree(found.id);
      loadMemberRewards(found.id);
    }
  };

  const formatRewardTypeLabel = (rewardType) => {
    if (rewardType === 'PLAYER_STACK') {
      return 'Бесплатный стартовый стек';
    }
    if (rewardType === 'INFLUENCER_FIRST_TOURNAMENT') {
      return 'Инфлюенсер: первый турнир реферала';
    }
    if (rewardType === 'INFLUENCER_DEPOSIT_PERCENT') {
      return 'Инфлюенсер: процент с депозитов';
    }
    if (!rewardType) {
      return 'Вознаграждение';
    }
    return 'Другое вознаграждение';
  };

  const memberTotalStackCount =
    memberRewardsData && memberRewardsData.summary &&
    typeof memberRewardsData.summary.total_stack_count === 'number'
      ? memberRewardsData.summary.total_stack_count
      : 0;

  const memberTotalInfluencerAmount =
    memberRewardsData && memberRewardsData.summary
      ? memberRewardsData.summary.total_influencer_amount
      : 0;

  const memberTotalFirstTournamentAmount =
    memberRewardsData && memberRewardsData.summary
      ? memberRewardsData.summary.total_first_tournament_amount
      : 0;

  const memberTotalDepositPercentAmount =
    memberRewardsData && memberRewardsData.summary
      ? memberRewardsData.summary.total_deposit_percent_amount
      : 0;

  const memberRewardsList = Array.isArray(memberRewardsData?.rewards)
    ? memberRewardsData.rewards
    : Array.isArray(memberRewardsData?.items)
    ? memberRewardsData.items
    : Array.isArray(memberRewardsData)
    ? memberRewardsData
    : [];

  const currentUserType =
    member && member.user_type
      ? member.user_type
      : member && member.is_influencer
      ? 'influencer'
      : 'player';
  const currentRank = member && member.rank ? member.rank : 'standard';
  const currentRankRule = member && member.current_rank_rule ? member.current_rank_rule : null;

  const playerMultiplier = currentRankRule
    ? Number(currentRankRule.player_depth_bonus_multiplier || 1)
    : 1;
  const influencerMultiplier = currentRankRule
    ? Number(currentRankRule.influencer_depth_bonus_multiplier || 1)
    : 1;

  const playerDepthBonus = 100 * playerMultiplier;
  const influencerDepthBonus = 50 * influencerMultiplier;

  return (
    <main
      data-easytag="id1-react/src/components/Admin/Referrals.jsx"
      className="page-admin-referrals-inner"
    >
      <section className="card admin-section-header">
        <h2 className="section-title">Реферальные события</h2>
        <p className="section-subtitle">
          Все регистрации по реферальным ссылкам, депозиты и начисленные бонусы.
        </p>

        {member && (
          <p className="admin-chart-subtitle">
            Ваш текущий ранг: {getRankLabel(currentRank)}.{' '}
            {currentUserType === 'influencer'
              ? `За первый турнир прямого реферала вы получаете 500 ₽, а за рефералов на уровнях 2–10 — около ${influencerDepthBonus} ₽ за первый турнир каждого игрока (множитель глубинного кэшбэка по рангу). Дополнительно вы всегда получаете 10% со всех дальнейших депозитов прямых рефералов.`
              : `За прямого реферала вы получаете 1000 V-Coins за его первый турнир, а за рефералов на уровнях 2–10 — около ${playerDepthBonus} V-Coins за первый турнир каждого игрока в глубину (множитель глубинного кэшбэка по рангу).`}
          </p>
        )}
      </section>

      <section className="card admin-filters-card">
        <h3 className="admin-filters-title">Фильтры</h3>

        <div className="admin-filters-grid">
          <div className="admin-filter-item">
            <label className="admin-filter-label" htmlFor="typeFilter">
              Тип реферера
            </label>
            <select
              id="typeFilter"
              className="admin-filter-select"
              value={typeFilter}
              onChange={handleTypeFilterChange}
            >
              <option value="all">Все</option>
              <option value="influencers">Только инфлюенсеры</option>
              <option value="regular">Только обычные игроки</option>
            </select>
          </div>

          <div className="admin-filter-item">
            <label className="admin-filter-label" htmlFor="fromDate">
              Дата от
            </label>
            <input
              id="fromDate"
              type="date"
              className="admin-filter-input"
              value={fromDate}
              onChange={handleFromDateChange}
            />
          </div>

          <div className="admin-filter-item">
            <label className="admin-filter-label" htmlFor="toDate">
              Дата до
            </label>
            <input
              id="toDate"
              type="date"
              className="admin-filter-input"
              value={toDate}
              onChange={handleToDateChange}
            />
          </div>
        </div>
      </section>

      <section className="card admin-form-card">
        <h3 className="admin-form-title">Добавить депозит по реферальной ссылке</h3>
        <p className="admin-form-subtitle">
          Укажите ID приглашённого игрока и сумму депозита (стоимость стека или докупки).
          Вознаграждение рефереру и глубинные бонусы будут рассчитаны автоматически по
          правилам ранговой программы.
        </p>

        {createError && <p className="admin-form-error">{createError}</p>}
        {createSuccess && <p className="admin-form-success">{createSuccess}</p>}

        <form className="admin-form" onSubmit={handleCreateReferralEvent}>
          <div className="admin-form-grid">
            <div className="admin-form-field">
              <label className="admin-form-label" htmlFor="createReferredId">
                ID реферала
              </label>
              <input
                id="createReferredId"
                type="number"
                className="admin-form-input"
                value={createReferredId}
                onChange={(event) => setCreateReferredId(event.target.value)}
                placeholder="Например, 102"
                min="1"
              />
              <p className="admin-form-help">
                Можно ввести ID вручную или выбрать пользователя ниже — тогда поле
                заполнится автоматически.
              </p>
            </div>

            <div className="admin-form-field">
              <label className="admin-form-label" htmlFor="createDepositAmount">
                Сумма депозита, ₽
              </label>
              <input
                id="createDepositAmount"
                type="number"
                className="admin-form-input"
                value={createDepositAmount}
                onChange={(event) => setCreateDepositAmount(event.target.value)}
                min="1"
                step="1"
              />
              <p className="admin-form-help">По умолчанию равна стоимости одного стека.</p>
            </div>

            <div className="admin-form-field">
              <label className="admin-form-label" htmlFor="createDateTime">
                Дата и время (необязательно)
              </label>
              <input
                id="createDateTime"
                type="datetime-local"
                className="admin-form-input"
                value={createDateTime}
                onChange={(event) => setCreateDateTime(event.target.value)}
              />
              <p className="admin-form-help">
                Если не заполнено, будет использовано текущее время создания события.
              </p>
            </div>
          </div>

          <div className="admin-form-actions">
            <button
              type="submit"
              className="btn btn-primary"
              disabled={createLoading}
            >
              {createLoading ? 'Создание...' : 'Зафиксировать депозит'}
            </button>
          </div>
        </form>
      </section>

      <section className="card admin-member-referral-card">
        <h3 className="admin-form-title">Структура и вознаграждения по пользователю</h3>
        <p className="admin-form-subtitle">
          Найдите пользователя и посмотрите его реферальное дерево и все начисленные
          вознаграждения в глубину структуры.
        </p>

        <form className="admin-member-search-row" onSubmit={handleMemberSearchSubmit}>
          <div className="admin-member-search-main">
            <label className="admin-form-label" htmlFor="memberSearchQuery">
              Поиск пользователя
            </label>
            <input
              id="memberSearchQuery"
              type="text"
              className="admin-form-input admin-member-search-input"
              placeholder="Имя, фамилия, телефон или ID"
              value={memberSearchQuery}
              onChange={(event) => setMemberSearchQuery(event.target.value)}
            />
          </div>

          <div className="admin-member-search-actions">
            <button
              type="submit"
              className="btn btn-secondary"
              disabled={memberSearchLoading}
            >
              {memberSearchLoading ? 'Поиск...' : 'Найти'}
            </button>
          </div>
        </form>

        {memberSearchError && (
          <p className="admin-member-error">{memberSearchError}</p>
        )}

        {memberSearchResults.length > 0 && (
          <div className="admin-member-select-row">
            <div className="admin-form-field">
              <label className="admin-form-label" htmlFor="selectedMemberId">
                Выберите пользователя из списка
              </label>
              <select
                id="selectedMemberId"
                className="admin-form-input admin-member-select"
                value={selectedMemberId}
                onChange={handleSelectedMemberChange}
              >
                <option value="">Не выбран</option>
                {memberSearchResults.map((user) => {
                  const fullName = `${user.first_name || ''} ${user.last_name || ''}`.trim();
                  const label = fullName || user.phone || `ID ${user.id}`;

                  return (
                    <option key={user.id} value={user.id}>
                      {label} (ID {user.id})
                    </option>
                  );
                })}
              </select>
            </div>
          </div>
        )}

        {selectedMember && (
          <>
            <div className="admin-selected-member">
              <span className="admin-selected-member-label">Выбранный пользователь:</span>
              <span className="admin-selected-member-name">
                {selectedMember.first_name} {selectedMember.last_name}{' '}
                {selectedMember.phone ? `· ${selectedMember.phone}` : ''}
              </span>
            </div>

            <div className="admin-member-sections-grid">
              <div className="admin-member-section">
                <h4 className="admin-subsection-title">Структура рефералов пользователя</h4>
                <p className="admin-subsection-caption">
                  Все игроки в структуре выбранного пользователя с указанием уровня,
                  ранга и статуса активации.
                </p>

                {memberTreeLoading && (
                  <p className="admin-member-loading">Загрузка структуры...</p>
                )}

                {memberTreeError && !memberTreeLoading && (
                  <p className="admin-member-error">{memberTreeError}</p>
                )}

                {!memberTreeLoading && !memberTreeError && (
                  memberTreeData.length === 0 ? (
                    <p className="admin-member-empty">
                      У пользователя пока нет рефералов.
                    </p>
                  ) : (
                    <div className="table-wrapper">
                      <table className="table admin-table">
                        <thead>
                          <tr>
                            <th>Пользователь</th>
                            <th>Тип</th>
                            <th>Ранг</th>
                            <th>Уровень</th>
                            <th>Активность</th>
                            <th>Бонус за первый турнир</th>
                          </tr>
                        </thead>
                        <tbody>
                          {memberTreeData.map((node, index) => {
                            const displayName = node && node.username
                              ? node.username
                              : node && node.descendant_id
                              ? `ID ${node.descendant_id}`
                              : '-';

                            const level =
                              typeof node.level === 'number' && node.level > 0 ? node.level : 0;

                            const nodeUserType = node && node.user_type ? node.user_type : 'player';
                            const nodeTypeLabel = getUserTypeLabel(nodeUserType);

                            const nodeRankLabel = getRankLabel(node && node.rank ? node.rank : 'standard');

                            const isActive = Boolean(
                              (node && node.is_active_referral) || (node && node.has_paid_first_bonus)
                            );

                            const hasPaidFirstBonus = Boolean(node && node.has_paid_first_bonus);

                            return (
                              <tr key={node.descendant_id || index}>
                                <td>{displayName}</td>
                                <td>{nodeTypeLabel}</td>
                                <td>{nodeRankLabel}</td>
                                <td>{level}</td>
                                <td>{isActive ? 'Активный' : 'Неактивный'}</td>
                                <td>{hasPaidFirstBonus ? 'Выплачен' : 'Не выплачен'}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )
                )}
              </div>

              <div className="admin-member-section">
                <h4 className="admin-subsection-title">Вознаграждения пользователя</h4>
                <p className="admin-subsection-caption">
                  Сводка бесплатных стеков и денежных выплат, начисленных выбранному
                  пользователю по всей структуре.
                </p>

                <div className="admin-member-summary-grid">
                  <div className="admin-member-summary-card">
                    <div className="admin-stat-title">Бесплатные стеки</div>
                    <div className="admin-stat-value">{memberTotalStackCount}</div>
                    <div className="admin-stat-caption">
                      Общее количество бесплатных стартовых стеков.
                    </div>
                  </div>

                  <div className="admin-member-summary-card">
                    <div className="admin-stat-title">Сумма как инфлюенсера</div>
                    <div className="admin-stat-value">
                      {memberTotalInfluencerAmount}{' '}
                      <span className="admin-stat-unit">₽</span>
                    </div>
                    <div className="admin-stat-caption">
                      Сумма всех денежных вознаграждений по структуре.
                    </div>
                  </div>

                  {Number(memberTotalFirstTournamentAmount) > 0 && (
                    <div className="admin-member-summary-card">
                      <div className="admin-stat-title">Первые турниры</div>
                      <div className="admin-stat-value">
                        {memberTotalFirstTournamentAmount}{' '}
                        <span className="admin-stat-unit">₽</span>
                      </div>
                      <div className="admin-stat-caption">
                        500/1000 ₽ за первый турнир каждого приведённого игрока.
                      </div>
                    </div>
                  )}

                  {Number(memberTotalDepositPercentAmount) > 0 && (
                    <div className="admin-member-summary-card">
                      <div className="admin-stat-title">Процент с депозитов</div>
                      <div className="admin-stat-value">
                        {memberTotalDepositPercentAmount}{' '}
                        <span className="admin-stat-unit">₽</span>
                      </div>
                      <div className="admin-stat-caption">
                        10% со всех депозитов на фишки в структуре.
                      </div>
                    </div>
                  )}
                </div>

                {memberRewardsLoading && (
                  <p className="admin-member-loading">
                    Загрузка вознаграждений пользователя...
                  </p>
                )}

                {memberRewardsError && !memberRewardsLoading && (
                  <p className="admin-member-error">{memberRewardsError}</p>
                )}

                {!memberRewardsLoading && !memberRewardsError && (
                  memberRewardsList.length === 0 ? (
                    <p className="admin-member-empty">
                      Для этого пользователя пока нет начисленных вознаграждений.
                    </p>
                  ) : (
                    <div className="table-wrapper">
                      <table className="table admin-table">
                        <thead>
                          <tr>
                            <th>Дата</th>
                            <th>Тип</th>
                            <th>От кого</th>
                            <th>Сумма</th>
                          </tr>
                        </thead>
                        <tbody>
                          {memberRewardsList.map((reward, index) => {
                            const key = reward.id || index;

                            const sourceName =
                              reward && reward.source_member_name
                                ? reward.source_member_name
                                : reward && reward.source_member_full_name
                                ? reward.source_member_full_name
                                : reward && reward.referred_name
                                ? reward.referred_name
                                : '-';

                            const amountRub =
                              typeof reward.amount_rub === 'number'
                                ? reward.amount_rub
                                : reward && typeof reward.amount_rub === 'string'
                                ? Number(reward.amount_rub) || 0
                                : 0;

                            const stackCount =
                              typeof reward.stack_count === 'number'
                                ? reward.stack_count
                                : reward && typeof reward.stack_count === 'string'
                                ? Number(reward.stack_count) || 0
                                : 0;

                            let amountText = '—';

                            if (amountRub) {
                              amountText = `${amountRub} ₽`;
                            } else if (stackCount) {
                              amountText = `${stackCount} стек(ов)`;
                            }

                            return (
                              <tr key={key}>
                                <td>{formatDateTime(reward.created_at || reward.date)}</td>
                                <td>{formatRewardTypeLabel(reward.reward_type)}</td>
                                <td>{sourceName}</td>
                                <td>{amountText}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )
                )}
              </div>
            </div>
          </>
        )}
      </section>

      <section className="card admin-table-card">
        <div className="admin-table-header">
          <div>
            <h3 className="admin-table-title">Список реферальных событий</h3>
            <p className="admin-table-subtitle">Всего событий: {count}</p>
          </div>
        </div>

        {loading && (
          <p className="admin-table-loading">Загрузка реферальных событий...</p>
        )}

        {error && !loading && <p className="admin-table-error">{error}</p>}

        {!loading && !error && (
          <div className="table-wrapper">
            <table className="table admin-table">
              <thead>
                <tr>
                  <th>Дата</th>
                  <th>Реферер</th>
                  <th>Тип реферера</th>
                  <th>Реферал</th>
                  <th>Бонусы</th>
                  <th>Деньги</th>
                  <th>Депозит</th>
                </tr>
              </thead>
              <tbody>
                {referrals.length === 0 && (
                  <tr>
                    <td colSpan={7} className="admin-table-empty">
                      Реферальные события не найдены.
                    </td>
                  </tr>
                )}

                {referrals.map((item) => {
                  const referrerName = `${item.referrer.first_name} ${item.referrer.last_name}`;
                  const referredName = `${item.referred.first_name} ${item.referred.last_name}`;
                  const isInfluencer = Boolean(item.referrer_is_influencer);

                  return (
                    <tr key={item.id}>
                      <td>{formatDateTime(item.created_at)}</td>
                      <td>{referrerName}</td>
                      <td>{isInfluencer ? 'Инфлюенсер' : 'Обычный игрок'}</td>
                      <td>{referredName}</td>
                      <td>{item.bonus_amount}</td>
                      <td>{item.money_amount} ₽</td>
                      <td>{item.deposit_amount} ₽</td>
                    </tr>
                  );
                })}
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

export default AdminReferralsPage;
