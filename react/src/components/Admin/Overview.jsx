import React, { useEffect, useState, useMemo } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { fetchAdminStatsOverview } from '../../api/admin';
import { simulateAmirAlfiraDeposits } from '../../api/test';

const influencerColor = '#ff6cab';
const regularColor = '#4f46e5';
const gridColor = '#e5e7eb';
const pieColors = [influencerColor, regularColor];

const AdminOverviewPage = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [simulateLoading, setSimulateLoading] = useState(false);
  const [simulateError, setSimulateError] = useState('');
  const [simulateResult, setSimulateResult] = useState(null);

  useEffect(() => {
    let isCancelled = false;

    const loadStats = async () => {
      setLoading(true);
      setError('');

      try {
        const data = await fetchAdminStatsOverview();
        if (!isCancelled) {
          setStats(data);
        }
      } catch (err) {
        console.error('Failed to load admin stats overview', err);
        if (!isCancelled) {
          setError('Не удалось загрузить статистику. Пожалуйста, попробуйте позже.');
        }
      } finally {
        if (!isCancelled) {
          setLoading(false);
        }
      }
    };

    loadStats();

    return () => {
      isCancelled = true;
    };
  }, []);

  const handleSimulateDeposits = async () => {
    setSimulateError('');
    setSimulateResult(null);
    setSimulateLoading(true);

    try {
      const data = await simulateAmirAlfiraDeposits();
      setSimulateResult(data || null);
    } catch (err) {
      console.error('Failed to simulate deposits for Amir and Alfirа', err);
      setSimulateError(
        'Ошибка при моделировании депозитов. Попробуйте позже или проверьте права доступа.'
      );
    } finally {
      setSimulateLoading(false);
    }
  };

  const registrationsData = stats?.registrations_by_day || [];
  const topReferrersRaw = stats?.top_referrers || [];
  const incomeStats = stats?.income_by_source || {
    total_income: 0,
    income_from_influencers: 0,
    income_from_regular_users: 0,
  };

  const totalRegistrations = useMemo(() => {
    if (!registrationsData.length) {
      return 0;
    }

    return registrationsData.reduce((sum, item) => {
      const value = typeof item.count === 'number' ? item.count : 0;
      return sum + value;
    }, 0);
  }, [registrationsData]);

  const topReferrersData = useMemo(
    () =>
      topReferrersRaw.map((item) => ({
        id: item.id,
        name: `${item.first_name} ${item.last_name}`,
        is_influencer: item.is_influencer,
        total_referrals: item.total_referrals,
      })),
    [topReferrersRaw]
  );

  const incomeBySourceChartData = useMemo(
    () => [
      {
        name: 'Инфлюенсеры',
        value: incomeStats.income_from_influencers || 0,
      },
      {
        name: 'Обычные пользователи',
        value: incomeStats.income_from_regular_users || 0,
      },
    ],
    [incomeStats]
  );

  const hasAnyData = Boolean(
    registrationsData.length || topReferrersData.length || incomeStats.total_income
  );

  const simulateDeposits = simulateResult && Array.isArray(simulateResult.deposits)
    ? simulateResult.deposits
    : [];

  return (
    <main
      data-easytag="id1-react/src/components/Admin/Overview.jsx"
      className="page-admin-overview-inner"
    >
      <div className="card admin-section-header">
        <h2 className="section-title">Общая статистика</h2>
        <p className="section-subtitle">
          Регистрации по дням, топ рефереров и выручка по депозитам из реферальных ссылок.
        </p>

        <div className="admin-section-actions">
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleSimulateDeposits}
            disabled={simulateLoading}
          >
            {simulateLoading
              ? 'Моделирование депозитов...'
              : 'Смоделировать депозиты для Амира и Альфиры (по 2000 ₽)'}
          </button>
          <p className="admin-section-helper">
            Кнопка предназначена для тестового режима: создаёт или обновляет депозиты
            для пользователей «Амир» и «Альфира», показывая, как начисляются V-Coins и деньги
            по реферальной программе.
          </p>
        </div>
      </div>

      {simulateError && (
        <div className="card admin-error">
          <p>{simulateError}</p>
        </div>
      )}

      {simulateResult && (
        <section className="card admin-table-card">
          <div className="admin-table-header">
            <div>
              <h3 className="admin-table-title">Результаты моделирования депозитов</h3>
              <p className="admin-table-subtitle">
                Статус операции: {simulateResult.status || '—'}
              </p>
            </div>
          </div>

          {simulateDeposits.length === 0 ? (
            <p className="admin-table-empty">
              Данные по смоделированным депозитам отсутствуют.
            </p>
          ) : (
            <div className="table-wrapper">
              <table className="table admin-table">
                <thead>
                  <tr>
                    <th>ID пользователя</th>
                    <th>Имя</th>
                    <th>Телефон</th>
                    <th>Сумма депозита</th>
                    <th>Баланс V-Coins</th>
                    <th>Баланс денег, ₽</th>
                    <th>Новые реферальные изменения</th>
                  </tr>
                </thead>
                <tbody>
                  {simulateDeposits.map((item, index) => {
                    const member = item.member || {};
                    const fullName = `${member.first_name || ''} ${member.last_name || ''}`.trim() || '—';
                    const phone = member.phone || '—';
                    const amount = typeof item.amount === 'number' ? item.amount : 2000;

                    const vCoinsAfter =
                      typeof item.v_coins_balance_after !== 'undefined'
                        ? item.v_coins_balance_after
                        : member.v_coins_balance;

                    const cashAfter =
                      typeof item.cash_balance_after !== 'undefined'
                        ? item.cash_balance_after
                        : member.cash_balance;

                    const referralChanges = Array.isArray(item.referral_changes)
                      ? item.referral_changes
                      : [];

                    return (
                      <tr key={member.id || index}>
                        <td>{member.id || '—'}</td>
                        <td>{fullName}</td>
                        <td>{phone}</td>
                        <td>{amount} ₽</td>
                        <td>{vCoinsAfter || '0'}</td>
                        <td>{cashAfter || '0'} ₽</td>
                        <td>
                          {referralChanges.length === 0 && 'Без изменений'}
                          {referralChanges.length > 0 && (
                            <ul className="admin-referral-changes-list">
                              {referralChanges.map((change, changeIndex) => (
                                <li key={`${change.ancestor_id || 'a'}-${change.level || 0}-${changeIndex}`}>
                                  Предок ID {change.ancestor_id}, уровень {change.level}
                                </li>
                              ))}
                            </ul>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {loading && (
        <div className="card admin-loading">
          <p>Загрузка статистики...</p>
        </div>
      )}

      {error && !loading && (
        <div className="card admin-error">
          <p>{error}</p>
        </div>
      )}

      {!loading && !error && !hasAnyData && (
        <div className="card admin-empty">
          <p>Пока нет данных для отображения статистики.</p>
        </div>
      )}

      {!loading && !error && hasAnyData && (
        <>
          <section className="admin-cards-grid">
            <div className="card admin-stat-card admin-stat-card-primary">
              <h3 className="admin-stat-title">Всего регистраций</h3>
              <p className="admin-stat-value">{totalRegistrations}</p>
              <p className="admin-stat-caption">Суммарное количество регистраций по дням</p>
            </div>

            <div className="card admin-stat-card">
              <h3 className="admin-stat-title">Общий доход</h3>
              <p className="admin-stat-value">
                {incomeStats.total_income}
                {' '}
                <span className="admin-stat-unit">₽</span>
              </p>
              <p className="admin-stat-caption">
                Суммарная выручка по депозитам (стеки и докупки по реферальным ссылкам)
              </p>
            </div>

            <div className="card admin-stat-card">
              <h3 className="admin-stat-title">Доход от инфлюенсеров</h3>
              <p className="admin-stat-value">
                {incomeStats.income_from_influencers}
                {' '}
                <span className="admin-stat-unit">₽</span>
              </p>
              <p className="admin-stat-caption">
                Сумма депозитов клиентов, пришедших по ссылкам инфлюенсеров
              </p>
            </div>

            <div className="card admin-stat-card">
              <h3 className="admin-stat-title">Доход от обычных пользователей</h3>
              <p className="admin-stat-value">
                {incomeStats.income_from_regular_users}
                {' '}
                <span className="admin-stat-unit">₽</span>
              </p>
              <p className="admin-stat-caption">
                Сумма депозитов клиентов, пришедших по ссылкам обычных пользователей
              </p>
            </div>
          </section>

          <section className="admin-charts-grid">
            <div className="card admin-chart-card">
              <h3 className="admin-chart-title">Регистрации по дням</h3>
              <p className="admin-chart-subtitle">
                Регистрации и первые визиты по реферальным ссылкам.
              </p>
              <div className="admin-chart-wrapper">
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={registrationsData} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
                    <CartesianGrid stroke={gridColor} strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                    <Tooltip formatter={(value) => [value, 'Регистрации']} />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="count"
                      name="Регистрации"
                      stroke={regularColor}
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      activeDot={{ r: 5 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="card admin-chart-card">
              <h3 className="admin-chart-title">Топ рефереров</h3>
              <p className="admin-chart-subtitle">
                Сравнение самых эффективных рефереров по количеству клиентов.
              </p>
              <div className="admin-chart-wrapper">
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart
                    data={topReferrersData}
                    margin={{ top: 10, right: 16, bottom: 40, left: 0 }}
                  >
                    <CartesianGrid stroke={gridColor} strokeDasharray="3 3" />
                    <XAxis
                      dataKey="name"
                      tick={{ fontSize: 11 }}
                      interval={0}
                      angle={-30}
                      textAnchor="end"
                      height={60}
                    />
                    <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                    <Tooltip
                      formatter={(value) => [value, 'Всего рефералов']}
                      labelFormatter={(label) => `Реферер: ${label}`}
                    />
                    <Legend />
                    <Bar dataKey="total_referrals" name="Рефералы" radius={[4, 4, 0, 0]}>
                      {topReferrersData.map((item) => (
                        <Cell
                          key={item.id}
                          fill={item.is_influencer ? influencerColor : regularColor}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="card admin-chart-card admin-chart-card-wide">
              <h3 className="admin-chart-title">Доход по источникам</h3>
              <p className="admin-chart-subtitle">
                Сравнение суммарных депозитов (стеки и докупки) по источникам трафика.
              </p>
              <div className="admin-chart-wrapper admin-chart-wrapper-pie">
                <ResponsiveContainer width="100%" height={260}>
                  <PieChart>
                    <Tooltip formatter={(value) => [`${value} ₽`, 'Доход']} />
                    <Legend />
                    <Pie
                      data={incomeBySourceChartData}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={60}
                      outerRadius={90}
                      paddingAngle={2}
                    >
                      {incomeBySourceChartData.map((entry, index) => (
                        <Cell key={entry.name} fill={pieColors[index % pieColors.length]} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </section>
        </>
      )}
    </main>
  );
};

export default AdminOverviewPage;
