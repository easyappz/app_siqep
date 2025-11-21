import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { loginMember } from '../../../api/auth';
import { useAuth } from '../../../context/AuthContext';

const LoginPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState(
    location.state && location.state.fromRegistration
      ? 'Регистрация прошла успешно, теперь войдите в систему.'
      : ''
  );

  const handleSubmit = async (event) => {
    event.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');

    if (!phone || !password) {
      setErrorMessage('Пожалуйста, заполните все обязательные поля.');
      return;
    }

    if (password.length < 6) {
      setErrorMessage('Пароль должен содержать не менее 6 символов.');
      return;
    }

    setIsSubmitting(true);

    try {
      const data = await loginMember({ phone, password });
      const { token, member } = data || {};

      if (!token || !member) {
        setErrorMessage('Не удалось выполнить вход. Попробуйте ещё раз.');
        return;
      }

      login(token, member);

      if (member && member.is_admin) {
        navigate('/react-admin/overview');
      } else {
        navigate('/profile');
      }
    } catch (error) {
      console.error('Login error', error);

      let backendMessage = '';

      if (error && error.response && error.response.data) {
        const data = error.response.data;

        if (Array.isArray(data.non_field_errors) && data.non_field_errors.length > 0) {
          backendMessage = data.non_field_errors[0];
        } else if (typeof data.detail === 'string') {
          backendMessage = data.detail;
        }
      }

      setErrorMessage(
        backendMessage || 'Неверный номер телефона или пароль.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main
      data-easytag="id1-react/src/components/Auth/Login/index.jsx"
      className="page auth-page page-login"
    >
      <div className="container auth-container">
        <div className="card auth-card">
          <h1 className="auth-title">Вход по номеру телефона</h1>
          <p className="auth-subtitle">
            Введите номер телефона и пароль, чтобы попасть в личный кабинет или
            админ-панель.
          </p>

          <form className="auth-form" onSubmit={handleSubmit}>
            <div className="auth-form-group">
              <label htmlFor="phone" className="auth-label">
                Номер телефона
              </label>
              <input
                id="phone"
                name="phone"
                type="tel"
                className="auth-input"
                placeholder="Например, +7 900 000-00-00"
                value={phone}
                onChange={(event) => setPhone(event.target.value)}
                required
              />
            </div>

            <div className="auth-form-group">
              <label htmlFor="password" className="auth-label">
                Пароль
              </label>
              <input
                id="password"
                name="password"
                type="password"
                className="auth-input"
                placeholder="Введите пароль"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                minLength={6}
              />
            </div>

            <div className="auth-form-group auth-form-group-inline">
              <div className="auth-helper-inline">
                <Link to="/password-reset" className="auth-link">
                  Забыли пароль?
                </Link>
              </div>
            </div>

            {errorMessage && (
              <div className="auth-message auth-message-error">{errorMessage}</div>
            )}

            {successMessage && (
              <div className="auth-message auth-message-success">{successMessage}</div>
            )}

            <div className="auth-form-footer">
              <button
                type="submit"
                className="btn btn-primary auth-submit-btn"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Загрузка...' : 'Войти'}
              </button>
            </div>

            <p className="auth-helper-text">
              Нет аккаунта?{' '}
              <Link to="/register" className="auth-link">
                Зарегистрируйтесь
              </Link>
            </p>
          </form>
        </div>
      </div>
    </main>
  );
};

export default LoginPage;
