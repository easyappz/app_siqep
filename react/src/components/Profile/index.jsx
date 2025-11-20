import React, { useCallback, useContext, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from 'recharts';
import { AuthContext, useAuth } from '../../context/AuthContext';
import { fetchProfileStats } from '../../api/profile';
import { fetchReferralTree, fetchReferralRewards } from '../../api/referrals';

const ProfilePage = () => {
  const { member } = useContext(AuthContext);
  const { logout } = useAuth();
  const navigate = useNavigate();

  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copyStatus, setCopyStatus] = useState('');

  const [treeData, setTreeData] = useState([]);
  const [isLoadingTree, setIsLoadingTree] = useState(false);
  const [treeError, setTreeError] = useState('');

  const [rewardsData, setRewardsData] = useState(null);
  const [isLoadingRewards, setIsLoadingRewards] = useState(false);
  const [rewardsError, setRewardsError] = useState('');

  const handleCopyLink = async (link) => {
    if (!link) {
      return;
    }

    try {
      if (
        typeof navigator !== 'undefined' &&
        navigator.clipboard &&
        navigator.clipboard.writeText
      ) {
        await navigator.clipboard.writeText(link);
        setCopyStatus('Скопировано');
      } else {
        setCopyStatus('Скопируйте ссылку вручную');
      }
    } catch (copyError) {
      setCopyStatus('Не удалось скопировать');
    }

    window.setTimeout(() => {
      setCopyStatus('');
    }, 2000);
  };

  const loadStats = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const data = await fetchProfileStats();
      setStats(data || null);
    } catch (err) {
      const status = err && err.response ? err.response.status : null;

      if (status === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }

      setError('Не удалось загрузить статистику. Попробуйте еще раз.');
    } finally {
      setLoading(false);
    }
  }, [logout, navigate]);

  const loadReferralTree = useCallback(async () => {
    setIsLoadingTree(true);
    setTreeError('');

    try {
      const data = await fetchReferralTree();
      const nodes = Array.isArray(data?.nodes)
        ? data.nodes
        : Array.isArray(data)
        ? data
        : [];
      setTreeData(nodes);
    } catch (err) {
      const status = err && err.response ? err.response.status : null;

      if (status === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }

      setTreeError('Не удалось загрузить структуру рефералов. Попробуйте позже.');
    } finally {
      setIsLoadingTree(false);
    }
  }, [logout, navigate]);

  const loadReferralRewards = useCallback(async () => {
    setIsLoadingRewards(true);
    setRewardsError('');

    try {
      const data = await fetchReferralRewards();
      setRewardsData(data || null);
    } catch (err) {
      const status = err && err.response ? err.response.status : null;

      if (status === 401) {
        logout();
        navigate('/login', { replace: true });
        return;
      }

      setRewardsError('Не удалось загрузить вознаграждения. Попробуйте позже.');
    } finally {
      setIsLoadingRewards(false);
    }
  }, [logout, navigate]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  useEffect(() => {
    loadReferralTree();
    loadReferralRewards();
  }, [loadReferralTree, loadReferralRewards]);

  const referralCode = member && member.referral_code ? member.referral_code : '';

  const referralLink =
    typeof window !== 'undefined'
      ? `${window.location.origin}/register${referralCode ? `?ref=${referralCode}` : ''}`
      : '';

  const accountTypeLabel =
    member && member.is_influencer ? 'Инфлюенсер' : 'Игрок';

  const totalReferrals =
    stats && typeof stats.total_referrals !== 'undefined' ? stats.total_referrals : 0;

  const activeReferrals =
    stats && typeof stats.active_referrals !== 'undefined' ? stats.active_referrals : 0;

  const totalBonusPoints =
    stats && typeof stats.total_bonus_points !== 'undefined'
      ? stats.total_bonus_points
      : 0;

  const totalMoneyEarned =
    stats && typeof stats.total_money_earned !== 'undefined'
      ? stats.total_money_earned
      : 0;

  const chartData =
    stats && Array.isArray(stats.registrations_chart) ? stats.registrations_chart : [];

  const history = stats && Array.isArray(stats.history) ? stats.history : [];

  const totalStackCount =
    rewardsData && typeof rewardsData.total_stack_count === 'number'
      ? rewardsData.total_stack_count
      : 0;

  const totalInfluencerAmount =
    rewardsData && typeof rewardsData.total_influencer_amount === 'number'
      ? rewardsData.total_influencer_amount
      : 0;

  const totalFirstTournamentAmount =
    rewardsData && typeof rewardsData.total_first_tournament_amount === 'number'
      ? rewardsData.total_first_tournament_amount
      : 0;

  const totalDepositPercentAmount =
    rewardsData && typeof rewardsData.total_deposit_percent_amount === 'number'
      ? rewardsData.total_deposit_percent_amount
      : 0;

  const rewardsList = Array.isArray(rewardsData?.rewards)
    ? rewardsData.rewards
    : Array.isArray(rewardsData?.items)
    ? rewardsData.items
    : Array.isArray(rewardsData)
    ? rewardsData
    : [];

  const handleRetry = () => {
    loadStats();
    loadReferralTree();
    loadReferralRewards();
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

  const formatRewardDateTime = (isoValue) => {
    if (!isoValue) {
      return '—';
    }

    try {
      const date = new Date(isoValue);
      if (Number.isNaN(date.getTime())) {
        return isoValue;
      }
      return date.toLocaleString('ru-RU');
    } catch (dateError) {
      return isoValue;
    }
  };

  const formatStackText = (count) => {
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
  };

  return (
    <main
      data-easytag="id1-react/src/components/Profile/index.jsx"
      className="page page-profile"
    >
      <div className="container">
        <div className="profile-grid">
          <section className="card profile-header-card">
            <h1 className="page-title">Профиль пользователя</h1>
            <p className="page-subtitle">
              Ваш персональный кабинет участника реферальной программы покерного клуба.
              Здесь видно, какой у вас статус, сколько игроков в структуре и сколько вы
              уже заработали.
            </p>

            <div className="profile-info-grid">
              <div className="profile-info-column">
                <div className="profile-info-row">
                  <div className="profile-label">Имя</div>
                  <div className="profile-value">
                    {member && member.first_name ? member.first_name : '—'}
                  </div>
                </div>
                <div className="profile-info-row">
                  <div className="profile-label">Фамилия</div>
                  <div className="profile-value">
                    {member && member.last_name ? member.last_name : '—'}
                  </div>
                </div>
              </div>

              <div className="profile-info-column">
                <div className="profile-info-row">
                  <div className="profile-label">Телефон</div>
                  <div className="profile-value">
                    {member && member.phone ? member.phone : '—'}
                  </div>
                </div>
                <div className="profile-info-row">
                  <div className="profile-label">Email</div>
                  <div className="profile-value">
                    {member && member.email ? member.email : '—'}
                  </div>
                </div>
              </div>

              <div className="profile-info-column">
                <div className="profile-info-row">
                  <div className="profile-label">Статус</div>
                  <div className="profile-tag">{accountTypeLabel}</div>
                </div>
                {referralCode && (
                  <div className="profile-info-row">
                    <div className="profile-label">Реферальный код</div>
                    <div className="profile-value">{referralCode}</div>
                  </div>
                )}
              </div>
            </div>
          </section>

          <section className="card profile-referral-card">
            <h2 className="profile-section-title">Реферальная программа</h2>
            <p className="profile-section-text">
              Делитесь персональной ссылкой, приглашайте новых игроков в офлайн покерный
              клуб и получайте вознаграждения в глубину всей вашей структуры.
            </p>

            <div className="profile-referral-block">
              <div className="profile-label">Ваша реферальная ссылка</div>
              <div className="profile-referral-input-row">
                <input
                  type="text"
                  readOnly
                  value={referralLink}
                  className="profile-referral-input"
                />
                <button
                  type="button"
                  className="btn btn-primary profile-referral-copy-btn"
                  onClick={() => handleCopyLink(referralLink)}
                  disabled={!referralLink}
                >
                  Скопировать
                </button>
              </div>

              {copyStatus && <div className="profile-copy-status">{copyStatus}</div>}
            </div>

            <ul className="profile-rules-list">
              <li>
                Вы получаете 1 бесплатный стартовый стек (1000 ₽ участие в турнире) за
                каждого нового игрока в вашей структуре, который впервые приходит в клуб по
                вашей ссылке или по ссылке ваших рефералов.
              </li>
              <li>
                Если вы инфлюенсер, вы дополнительно получаете 1000 ₽ за первый турнир
                каждого реферала и 10% со всех его дальнейших депозитов на фишки.
              </li>
              <li>
                Структура работает в глубину: если ваш реферал приглашает новых игроков,
                вы тоже получаете свои бонусы в соответствии с правилами программы.
              </li>
            </ul>
          </section>
        </div>

        {loading && (
          <div className="profile-status-message">Загрузка статистики...</div>
        )}

        {!loading && error && (
          <div className="profile-status-message profile-status-error">
            <span>{error}</span>
            <button
              type="button"
              className="btn btn-outline profile-retry-btn"
              onClick={handleRetry}
            >
              Повторить попытку
            </button>
          </div>
        )}

        <section className="profile-stats-section">
          <div className="profile-stats-grid">
            <div className="card profile-stat-card">
              <div className="profile-stat-label">Количество рефералов</div>
              <div className="profile-stat-value">{totalReferrals}</div>
              <div className="profile-stat-caption">
                Все игроки, которые впервые пришли в покерный клуб по вашей ссылке или
                ссылкам ваших рефералов.
              </div>
            </div>

            <div className="card profile-stat-card">
              <div className="profile-stat-label">Активные рефералы</div>
              <div className="profile-stat-value">{activeReferrals}</div>
              <div className="profile-stat-caption">
                Рефералы, которые посещали клуб или делали депозиты на фишки за последние 30
                дней.
              </div>
            </div>

            <div className="card profile-stat-card">
              <div className="profile-stat-label">Бесплатные стартовые стеки</div>
              <div className="profile-stat-value">{totalBonusPoints}</div>
              <div className="profile-stat-caption">
                Каждый бонус = один бесплатный стартовый стек (1000 ₽ участие в турнире).
              </div>
            </div>

            {member && member.is_influencer && (
              <div className="card profile-stat-card profile-stat-card-accent">
                <div className="profile-stat-label">Заработано денег</div>
                <div className="profile-stat-value">{`${totalMoneyEarned} ₽`}</div>
                <div className="profile-stat-caption">
                  1000 ₽ за первый турнир каждого реферала + 10% с последующих депозитов на
                  фишки по вашей структуре.
                </div>
              </div>
            )}
          </div>
        </section>

        <section className="card profile-tree-card">
          <div className="profile-tree-header">
            <h2 className="profile-section-title">Моя структура рефералов</h2>
            <p className="profile-section-text">
              Список всех игроков в вашей реферальной структуре с указанием уровня,
              статуса и количества рефералов в глубину.
            </p>
          </div>

          {isLoadingTree && (
            <div className="profile-tree-loading">Загрузка структуры...</div>
          )}

          {treeError && !isLoadingTree && (
            <div className="profile-tree-error">{treeError}</div>
          )}

          {!isLoadingTree && !treeError && (
            treeData.length === 0 ? (
              <div className="profile-tree-empty">
                У вас пока нет рефералов. Поделитесь реферальной ссылкой, чтобы начать
                строить структуру.
              </div>
            ) : (
              <div className="profile-tree-table-wrapper">
                <table className="profile-tree-table">
                  <thead>
                    <tr>
                      <th>Имя / Ник</th>
                      <th>Уровень</th>
                      <th>Статус</th>
                      <th>Прямых рефералов</th>
                      <th>Всего в глубину</th>
                    </tr>
                  </thead>
                  <tbody>
                    {treeData.map((node, index) => {
                      const displayName =
                        node && node.name
                          ? node.name
                          : node && node.username
                          ? node.username
                          : node && node.full_name
                          ? node.full_name
                          : node && node.phone
                          ? node.phone
                          : '-';

                      const level =
                        typeof node.level === 'number'
                          ? node.level
                          : typeof node.depth === 'number'
                          ? node.depth
                          : typeof node.tier === 'number'
                          ? node.tier
                          : 0;

                      const isInfluencerNode = Boolean(
                        node && (node.is_influencer || node.influencer)
                      );

                      const directCount =
                        typeof node.direct_referrals_count === 'number'
                          ? node.direct_referrals_count
                          : typeof node.direct_children_count === 'number'
                          ? node.direct_children_count
                          : typeof node.direct_count === 'number'
                          ? node.direct_count
                          : 0;

                      const totalCount =
                        typeof node.total_descendants_count === 'number'
                          ? node.total_descendants_count
                          : typeof node.total_in_structure === 'number'
                          ? node.total_in_structure
                          : typeof node.total_count === 'number'
                          ? node.total_count
                          : 0;

                      return (
                        <tr key={node.id || index}>
                          <td>{displayName}</td>
                          <td>{level}</td>
                          <td>{isInfluencerNode ? 'Инфлюенсер' : 'Игрок'}</td>
                          <td>{directCount}</td>
                          <td>{totalCount}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )
          )}
        </section>

        <section className="card profile-rewards-card">
          <div className="profile-rewards-header">
            <h2 className="profile-section-title">Мои вознаграждения</h2>
            <p className="profile-section-text">
              Сводка бесплатных стартовых стеков и денежных вознаграждений, которые вы
              получили как игрок или инфлюенсер за всю глубину вашей структуры.
            </p>
          </div>

          <div className="profile-rewards-summary-grid">
            <div className="profile-rewards-summary-card">
              <div className="profile-stat-label">Бесплатные стартовые стеки</div>
              <div className="profile-stat-value">{totalStackCount}</div>
              <div className="profile-stat-caption">
                Суммарное количество стеков, начисленных за новых игроков в вашей структуре.
              </div>
            </div>

            <div className="profile-rewards-summary-card">
              <div className="profile-stat-label">Сумма вознаграждений как инфлюенсера</div>
              <div className="profile-stat-value">{`${totalInfluencerAmount} ₽`}</div>
              <div className="profile-stat-caption">
                Если у вас статус инфлюенсера, сюда входят все денежные выплаты по
                структуре.
              </div>
            </div>

            {totalFirstTournamentAmount > 0 && (
              <div className="profile-rewards-summary-card">
                <div className="profile-stat-label">За первые турниры рефералов</div>
                <div className="profile-stat-value">
                  {`${totalFirstTournamentAmount} ₽`}
                </div>
                <div className="profile-stat-caption">
                  Сумма 1000 ₽ за первый турнир каждого приведённого игрока.
                </div>
              </div>
            )}

            {totalDepositPercentAmount > 0 && (
              <div className="profile-rewards-summary-card">
                <div className="profile-stat-label">Процент с депозитов на фишки</div>
                <div className="profile-stat-value">
                  {`${totalDepositPercentAmount} ₽`}
                </div>
                <div className="profile-stat-caption">
                  10% со всех дальнейших депозитов на фишки ваших рефералов в глубину.
                </div>
              </div>
            )}
          </div>

          {isLoadingRewards && (
            <div className="profile-rewards-loading">Загрузка вознаграждений...</div>
          )}

          {rewardsError && !isLoadingRewards && (
            <div className="profile-rewards-error">{rewardsError}</div>
          )}

          {!isLoadingRewards && !rewardsError && (
            rewardsList.length === 0 ? (
              <div className="profile-rewards-empty">
                Пока нет начисленных вознаграждений. Приглашайте новых игроков, чтобы
                получать бесплатные стеки и денежные бонусы.
              </div>
            ) : (
              <div className="profile-rewards-table-wrapper">
                <table className="profile-rewards-table">
                  <thead>
                    <tr>
                      <th>Дата</th>
                      <th>Тип</th>
                      <th>От кого</th>
                      <th>Сумма</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rewardsList.map((reward, index) => {
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
                        amountText = formatStackText(stackCount);
                      }

                      return (
                        <tr key={key}>
                          <td>{formatRewardDateTime(reward.created_at || reward.date)}</td>
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
        </section>

        <section className="card profile-chart-card">
          <div className="profile-chart-header">
            <h2 className="profile-section-title">График регистраций</h2>
            <p className="profile-section-text">
              Динамика привлечения новых игроков по вашей реферальной ссылке и структуре.
            </p>
          </div>

          <div className="profile-chart-inner">
            {chartData.length === 0 ? (
              <div className="profile-chart-empty">
                Пока нет данных для отображения графика.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={chartData}
                  margin={{ top: 10, right: 20, left: -10, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.35)" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11, fill: '#e5e7eb' }}
                    stroke="rgba(148, 163, 184, 0.7)"
                  />
                  <YAxis
                    allowDecimals={false}
                    tick={{ fontSize: 11, fill: '#e5e7eb' }}
                    stroke="rgba(148, 163, 184, 0.7)"
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#020617',
                      borderRadius: '0.75rem',
                      border: '1px solid rgba(148, 163, 184, 0.6)',
                      color: '#e5e7eb',
                      fontSize: '0.85rem',
                    }}
                    labelStyle={{ color: '#f9fafb', marginBottom: 4 }}
                  />
                  <Legend
                    wrapperStyle={{ paddingTop: 8 }}
                    iconType="circle"
                    formatter={(value) => (
                      <span style={{ color: '#e5e7eb', fontSize: '0.85rem' }}>
                        {value === 'count' ? 'Регистрации' : value}
                      </span>
                    )}
                  />
                  <Line
                    type="monotone"
                    dataKey="count"
                    name="Регистрации"
                    stroke="#60a5fa"
                    strokeWidth={2.4}
                    dot={{
                      r: 4,
                      strokeWidth: 2,
                      stroke: '#1d4ed8',
                      fill: '#0ea5e9',
                    }}
                    activeDot={{
                      r: 6,
                      strokeWidth: 0,
                      fill: '#fb7185',
                    }}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </section>

        <section className="card profile-history-card">
          <div className="profile-history-header">
            <h2 className="profile-section-title">История начислений</h2>
            <p className="profile-section-text">
              Дополнительная история бонусов и выплат по вашим рефералам, включающая
              бесплатные стеки и денежные вознаграждения.
            </p>
          </div>

          {history.length === 0 ? (
            <div className="profile-history-empty">
              Пока нет начислений. Поделитесь реферальной ссылкой, чтобы начать
              зарабатывать.
            </div>
          ) : (
            <div className="profile-history-table-wrapper">
              <table className="profile-history-table">
                <thead>
                  <tr>
                    <th>Дата</th>
                    <th>Реферал</th>
                    <th>Бонусы</th>
                    <th>Деньги</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((entry, index) => {
                    const referralName =
                      entry && entry.referred_name
                        ? entry.referred_name
                        : entry && entry.referred_full_name
                        ? entry.referred_full_name
                        : '-';

                    const bonus =
                      typeof entry.bonus_amount === 'number'
                        ? entry.bonus_amount
                        : entry.bonus_amount || 0;

                    const money =
                      typeof entry.money_amount === 'number'
                        ? entry.money_amount
                        : entry.money_amount || 0;

                    return (
                      <tr key={entry.id || index}>
                        <td>{entry.date || '—'}</td>
                        <td>{referralName}</td>
                        <td>{bonus}</td>
                        <td>{money ? `${money} ₽` : '—'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </main>
  );
};

export default ProfilePage;
