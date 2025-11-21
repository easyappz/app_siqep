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

const influencerColor = '#ff6cab';
const regularColor = '#4f46e5';
const gridColor = '#e5e7eb';
const pieColors = [influencerColor, regularColor];

const formatCurrency = (value) => {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '0 ₽';
  }

  return `${value} ₽`;
};

const AdminOverviewPage = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

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
      </div>

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
                  <LineChart
                    data={registrationsData}
                    margin={{ top: 10, right: 16, bottom: 0, left: 0 }}
                  >
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
