import React, { useEffect, useState } from 'react';
import { fetchAdminReferrals } from '../../api/admin';

const AdminReferralsPage = () => {
  const [referrals, setReferrals] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [typeFilter, setTypeFilter] = useState('all');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');

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

  return (
    <main
      data-easytag="id1-react/src/components/Admin/Referrals.jsx"
      className="page-admin-referrals-inner"
    >
      <section className="card admin-section-header">
        <h2 className="section-title">Реферальные события</h2>
        <p className="section-subtitle">
          Все регистрации по реферальным ссылкам и начисленные бонусы.
        </p>
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
              <option value="regular">Только обычные</option>
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
                      <td>{isInfluencer ? 'Инфлюенсер' : 'Обычный'}</td>
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
