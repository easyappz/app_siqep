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

const ProfilePage = () => {
  const { member } = useContext(AuthContext);
  const { logout } = useAuth();
  const navigate = useNavigate();

  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copyStatus, setCopyStatus] = useState('');

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

  useEffect(() => {
    loadStats();
  }, [loadStats]);

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

  const handleRetry = () => {
    loadStats();
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
              Статистика по реферальной программе покерного клуба: сколько игроков вы привели
              и сколько бесплатных стеков или денег заработали.
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
            <h2 className="profile-section-title">Ваша реферальная ссылка</h2>
            <p className="profile-section-text">
              Отправьте эту ссылку друзьям, гостям клуба или своей аудитории. Новые игроки
              приходят в офлайн покерный клуб по вашей ссылке, а система автоматически
              начисляет вам бесплатные стеки или деньги в зависимости от типа аккаунта.
            </p>

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

            <p className="profile-section-text">
              <strong>Правила программы.</strong> Игроки клуба получают 1 бесплатный
              стартовый стек (1000 ₽ участие в турнире) за каждого нового игрока, который
              впервые приходит в клуб по их ссылке. Инфлюенсеры получают 1000 ₽ за первый
              турнир реферала и 10% со всех его дальнейших депозитов на фишки.
            </p>
            <p className="profile-section-text">
              Статистика ниже (график и история начислений) помогает видеть динамику ваших
              приглашений, бесплатных стеков и денежного дохода.
            </p>
            <p className="profile-section-text">
              Пример: вы привели 5 новых игроков как инфлюенсер → минимум 5 000 ₽ за их
              первые турниры + дополнительный доход, если они продолжают играть и докупать
              фишки.
            </p>
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
                Все игроки, которые впервые пришли в покерный клуб по вашей реферальной
                ссылке.
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
              <div className="profile-stat-label">Заработано бесплатных стеков</div>
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
                  фишки.
                </div>
              </div>
            )}
          </div>
        </section>

        <section className="card profile-chart-card">
          <div className="profile-chart-header">
            <h2 className="profile-section-title">График регистраций</h2>
            <p className="profile-section-text">
              Динамика привлечения новых игроков по вашей реферальной ссылке.
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
              Подробная история бесплатных стеков и денежных начислений по вашим рефералам в
              покерном клубе.
            </p>
          </div>

          {history.length === 0 ? (
            <div className="profile-history-empty">
              Пока нет начислений. Поделитесь реферальной ссылкой, чтобы начать зарабатывать.
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
