import React, { useEffect, useMemo, useState } from 'react';
import { fetchAdminMembersReferrals, fetchMemberRewards } from '../../api/referrals';
import { useAuth } from '../../context/AuthContext';

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

function formatStackCount(count) {
  if (!count) {
    return '';
  }
  if (count === 1) {
    return '1 стек';
  }
  if (count >= 2 && count <= 4) {
    return `${count} стека`;
  }
  return `${count} стеков`;
}

function formatCurrencyValue(amount) {
  if (!Number.isFinite(amount) || amount <= 0) {
    return '';
  }
  return new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount);
}

function isReferralNodeActive(node) {
  if (!node) {
    return false;
  }
  if (node.status === 'active') {
    return true;
  }
  if (node.status === 'pending') {
    return false;
  }
  return Boolean(node.is_active_referral || node.has_paid_first_bonus);
}

function getReferralStatusLabel(node) {
  return isReferralNodeActive(node) ? 'Активный' : 'Ожидает пополнения';
}

function formatReferralRewardValue(rewardSummary) {
  if (!rewardSummary) {
    return '—';
  }
  if (rewardSummary.money > 0) {
    const formatted = formatCurrencyValue(rewardSummary.money);
    if (formatted) {
      return `${formatted} ₽`;
    }
  }
  if (rewardSummary.stacks > 0) {
    return formatStackCount(rewardSummary.stacks);
  }
  return '—';
}

const AdminReferralsPage = () => {
  const { member } = useAuth();
  const [selectedMemberId, setSelectedMemberId] = useState(member?.id || '');
  const [memberTreeData, setMemberTreeData] = useState([]);
  const [memberTreeLoading, setMemberTreeLoading] = useState(false);
  const [memberTreeError, setMemberTreeError] = useState('');

  const [memberRewardsData, setMemberRewardsData] = useState([]);
  const [memberRewardsLoading, setMemberRewardsLoading] = useState(false);
  const [memberRewardsError, setMemberRewardsError] = useState('');

  const [memberSearchQuery, setMemberSearchQuery] = useState('');

  const filteredMembers = memberTreeData.filter((node) =>
    (node.phone || '').includes(memberSearchQuery),
  );

  useEffect(() => {
    if (!selectedMemberId) {
      return;
    }

    const fetchData = async () => {
      setMemberTreeLoading(true);
      setMemberTreeError('');

      try {
        const data = await fetchAdminMembersReferrals(selectedMemberId);
        setMemberTreeData(Array.isArray(data) ? data : []);
      } catch (error) {
        setMemberTreeError('Не удалось загрузить дерево рефералов.');
      } finally {
        setMemberTreeLoading(false);
      }
    };

    fetchData();
  }, [selectedMemberId]);

  useEffect(() => {
    if (!selectedMemberId) {
      return;
    }

    const fetchRewardsData = async () => {
      setMemberRewardsLoading(true);
      setMemberRewardsError('');

      try {
        const data = await fetchMemberRewards(selectedMemberId);
        setMemberRewardsData(data);
      } catch (error) {
        setMemberRewardsError('Не удалось загрузить вознаграждения.');
      } finally {
        setMemberRewardsLoading(false);
      }
    };

    fetchRewardsData();
  }, [selectedMemberId]);

  const memberRewardsList = Array.isArray(memberRewardsData?.rewards)
    ? memberRewardsData.rewards
    : Array.isArray(memberRewardsData?.items)
    ? memberRewardsData.items
    : Array.isArray(memberRewardsData)
    ? memberRewardsData
    : [];

  const referralRewardsBySource = useMemo(() => {
    return memberRewardsList.reduce((acc, reward) => {
      const sourceId =
        reward && (reward.source_member || reward.source_member_id || reward.source_memberId);
      if (!sourceId) {
        return acc;
      }
      const money = Number(reward.amount_rub) || 0;
      const stacks = Number(reward.stack_count) || 0;
      const current = acc[sourceId] || { money: 0, stacks: 0 };
      current.money += money;
      current.stacks += stacks;
      acc[sourceId] = current;
      return acc;
    }, {});
  }, [memberRewardsList]);

  const memberActiveReferralsCount = useMemo(
    () => memberTreeData.filter((node) => isReferralNodeActive(node)).length,
    [memberTreeData],
  );

  const memberPendingReferralsCount = Math.max(
    memberTreeData.length - memberActiveReferralsCount,
    0,
  );

  const onSearchChange = (event) => {
    setMemberSearchQuery(event.target.value);
  };

  return (
    <main
      data-easytag="id3-react/src/components/Admin/Referrals.jsx"
      className="page-admin-referrals-inner"
    >
      <section className="card admin-section-header">
        <h2 className="section-title">Реферальная структура</h2>
        <p className="section-subtitle">
          Отслеживайте, сколько рефералов привёл участник и какие бонусы им начислены.
        </p>
      </section>

      <section className="card admin-filters-card">
        <h3 className="admin-form-title">Выбор участника</h3>
        <p className="admin-form-subtitle">
          Введите ID участника или его номер телефона, чтобы посмотреть его реферальную сеть.
        </p>

        <div className="admin-form-grid">
          <div className="admin-form-row">
            <label className="admin-form-label" htmlFor="memberId">
              ID или телефон участника
            </label>
            <input
              id="memberId"
              name="memberId"
              type="text"
              className="admin-form-input"
              value={selectedMemberId}
              onChange={(event) => setSelectedMemberId(event.target.value)}
              placeholder="Например, 105 или +79995556677"
            />
          </div>

          <div className="admin-form-row">
            <label className="admin-form-label" htmlFor="searchReferrals">
              Поиск по номеру телефона в дереве
            </label>
            <input
              id="searchReferrals"
              name="searchReferrals"
              type="text"
              className="admin-form-input"
              value={memberSearchQuery}
              onChange={onSearchChange}
              placeholder="Фильтр по телефону"
              disabled={memberTreeLoading || !memberTreeData.length}
            />
          </div>
        </div>
      </section>

      <section className="card admin-table-card">
        <div className="admin-table-header">
          <div>
            <h3 className="admin-table-title">Дерево рефералов</h3>
            <p className="admin-table-subtitle">
              Всего рефералов: {memberTreeData.length}
            </p>
          </div>
          {(memberTreeLoading || memberRewardsLoading) && (
            <div className="admin-table-loading">Загрузка данных...</div>
          )}
          {(memberTreeError || memberRewardsError) && (
            <div className="admin-table-error">
              {memberTreeError || memberRewardsError}
            </div>
          )}
        </div>

        {!memberTreeLoading && !memberTreeError && (
          memberTreeData.length === 0 ? (
            <p className="admin-member-empty">У пользователя пока нет рефералов.</p>
          ) : (
            <>
              <div className="admin-member-summary-grid">
                <div className="admin-member-summary-card">
                  <div className="admin-stat-title">Активные рефералы</div>
                  <div className="admin-stat-value">{memberActiveReferralsCount}</div>
                  <div className="admin-stat-caption">
                    Игроки, которые пополнили баланс и активировали бонус.
                  </div>
                </div>
                <div className="admin-member-summary-card">
                  <div className="admin-stat-title">Ожидают пополнения</div>
                  <div className="admin-stat-value">{memberPendingReferralsCount}</div>
                  <div className="admin-stat-caption">
                    Зарегистрированы, но ещё не совершен депозит.
                  </div>
                </div>
              </div>
              <div className="table-wrapper">
                <table className="table admin-table">
                  <thead>
                    <tr>
                      <th>Пользователь</th>
                      <th>Тип</th>
                      <th>Ранг</th>
                      <th>Уровень</th>
                      <th>Статус</th>
                      <th>Бонус за первый турнир</th>
                      <th>Вознаграждение</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(memberSearchQuery ? filteredMembers : memberTreeData).map((node) => {
                      const hasPaidFirstBonus = Boolean(node && node.has_paid_first_bonus);
                      const statusLabel = getReferralStatusLabel(node);
                      const rewardSummary =
                        node && node.descendant_id
                          ? referralRewardsBySource[node.descendant_id]
                          : null;
                      const rewardValue = formatReferralRewardValue(rewardSummary);

                      return (
                        <tr key={`${node.descendant_id}-${node.level}`}>
                          <td>
                            <div className="admin-member-name-cell">
                              <span>{node.phone || '—'}</span>
                              {node.is_influencer && (
                                <span className="admin-badge admin-badge-influencer">Инфлюенсер</span>
                              )}
                            </div>
                          </td>
                          <td>{node.member_type || 'Игрок'}</td>
                          <td>{getRankLabel(node.descendant_rank)}</td>
                          <td>{node.level}</td>
                          <td>{statusLabel}</td>
                          <td>{hasPaidFirstBonus ? 'Выплачен' : 'Не выплачен'}</td>
                          <td>{rewardValue}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </>
          )
        )}
      </section>
    </main>
  );
};

export default AdminReferralsPage;
