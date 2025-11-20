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
            <h1 className="page-title">Реферальная программа покерного клуба</h1>
            <p className="page-subtitle">
              Реферальная программа для офлайн покерного клуба без игры на реальные деньги.
              Гости покупают стартовый стек примерно за 1000 ₽ за участие в турнире и могут
              несколько раз докупать фишки в первые часы игры.
            </p>

            <div className="home-hero-highlight">
              <p>
                <strong>Игроки клуба:</strong> 1 бесплатный стартовый стек (1000 ₽ участие)
                за каждого нового друга, который впервые пришёл в клуб по вашей ссылке.
              </p>
              <p>
                <strong>Инфлюенсеры:</strong> 1000 ₽ за первый турнир приведённого игрока
                + 10% со всех следующих покупок фишек и новых турниров этого игрока.
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
              <div className="home-stat-label">Пример для инфлюенсера</div>
              <div className="home-stat-value">10 новых игроков = 10 000 ₽+</div>
              <p className="home-stat-caption">
                Если вы инфлюенсер и привели 10 новых игроков, вы получаете 1000 ₽ за их
                первые турниры (10 × 1000 ₽), а затем зарабатываете 10% со всех их
                последующих докупок фишек и новых турниров.
              </p>
            </div>
            <div className="home-stat-card home-stat-card-secondary">
              <div className="home-stat-label">Пример для игрока клуба</div>
              <div className="home-stat-value">3 друга = 3 бесплатных входа</div>
              <p className="home-stat-caption">
                Как игрок клуба вы получаете по одному бесплатному стартовому стеку (1000 ₽
                участие) за каждого из 3 друзей, которые впервые приходят в клуб по вашей
                ссылке.
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
                Создайте аккаунт по номеру телефона за пару минут. В профиле вы сразу
                получите персональную реферальную ссылку как игрок клуба или инфлюенсер.
              </p>
            </article>

            <article className="card home-info-card">
              <h3 className="home-info-title">2. Делитесь ссылкой</h3>
              <p className="home-info-text">
                Отправляйте ссылку друзьям и гостям офлайн покерного клуба или своей
                онлайн-аудитории. Система автоматически учитывает, кто впервые пришёл в клуб
                по вашей ссылке и какие депозиты на фишки они делают.
              </p>
            </article>

            <article className="card home-info-card">
              <h3 className="home-info-title">3. Получайте стеки и доход</h3>
              <p className="home-info-text">
                Игроки клуба копят бесплатные стартовые стеки, а инфлюенсеры получают 1000 ₽
                за первый турнир реферала и 10% со всех его дальнейших депозитов на фишки.
                Вся статистика и история начислений видны в личном кабинете.
              </p>
            </article>
          </div>
        </section>
      </div>
    </main>
  );
};

export default Home;
