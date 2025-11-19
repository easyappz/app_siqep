import React from 'react';
import { useNavigate } from 'react-router-dom';

export const Home = () => {
  const navigate = useNavigate();

  const handleGoToRegister = () => {
    navigate('/register');
  };

  const handleGoToLogin = () => {
    navigate('/login');
  };

  return (
    <main
      data-easytag="id1-react/src/components/Home/index.jsx"
      className="page page-home"
    >
      <div className="container">
        <section className="card home-hero">
          <div className="home-hero-main">
            <h1 className="page-title">Реферальная программа</h1>
            <p className="page-subtitle">
              Запускайте собственную реферальную программу: обычные пользователи
              зарабатывают бонусы, а инфлюенсеры получают реальные деньги за
              приведённых клиентов.
            </p>

            <div className="home-hero-highlight">
              <p>
                <strong>Обычные пользователи:</strong> 1 бонус за каждого
                приглашённого клиента.
              </p>
              <p>
                <strong>Инфлюенсеры:</strong> 20% (200 ₽) от каждого депозита
                клиента (1 депозит = 1000 ₽).
              </p>
            </div>

            <div className="home-hero-actions">
              <button
                type="button"
                className="btn btn-primary home-hero-btn"
                onClick={handleGoToRegister}
              >
                Зарегистрироваться
              </button>
              <button
                type="button"
                className="btn btn-outline home-hero-btn"
                onClick={handleGoToLogin}
              >
                Войти
              </button>
            </div>
          </div>

          <div className="home-hero-aside">
            <div className="home-stat-card">
              <div className="home-stat-label">Пример дохода инфлюенсера</div>
              <div className="home-stat-value">10 клиентов = 2 000 ₽</div>
              <p className="home-stat-caption">
                Каждый приглашённый клиент автоматически считается депозитом на
                1000 ₽, из которых вы получаете 20%.
              </p>
            </div>
            <div className="home-stat-card home-stat-card-secondary">
              <div className="home-stat-label">Бонусы для друзей</div>
              <div className="home-stat-value">1 друг = 1 бонус</div>
              <p className="home-stat-caption">
                Собирайте бонусы за активных друзей и отслеживайте статистику в
                личном кабинете.
              </p>
            </div>
          </div>
        </section>

        <section className="home-section">
          <h2 className="home-section-title">Как это работает</h2>
          <div className="home-cards-grid">
            <article className="card home-info-card">
              <h3 className="home-info-title">1. Зарегистрируйтесь</h3>
              <p className="home-info-text">
                Создайте аккаунт по номеру телефона за пару минут. В профиле вы
                сразу получите персональную реферальную ссылку.
              </p>
            </article>

            <article className="card home-info-card">
              <h3 className="home-info-title">2. Делитесь ссылкой</h3>
              <p className="home-info-text">
                Отправляйте ссылку друзьям, клиентам или аудитории. Мы
                автоматически считаем регистрации и депозиты по вашим
                рефералам.
              </p>
            </article>

            <article className="card home-info-card">
              <h3 className="home-info-title">3. Получайте бонусы и деньги</h3>
              <p className="home-info-text">
                Обычные пользователи копят бонусы, инфлюенсеры получают 20% от
                депозита каждого клиента. Вся статистика и графики доступны в
                удобной панели.
              </p>
            </article>
          </div>
        </section>
      </div>
    </main>
  );
};

export default Home;
