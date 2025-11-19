import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { registerMember } from '../../../api/auth';
import { useAuth } from '../../../context/AuthContext';

const RegisterPage = () => {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [formValues, setFormValues] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    email: '',
    password: '',
    referral_code: '',
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const search = window.location.search || '';
    if (!search) {
      return;
    }

    const params = new URLSearchParams(search);
    const refFromUrl = params.get('ref');

    if (refFromUrl) {
      setFormValues((prev) => ({
        ...prev,
        referral_code: prev.referral_code || refFromUrl,
      }));
    }
  }, []);

  const handleChange = (event) => {
    const { name, value } = event.target;

    setFormValues((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const validateForm = () => {
    if (!formValues.first_name || !formValues.last_name || !formValues.phone || !formValues.password) {
      setErrorMessage('Пожалуйста, заполните все обязательные поля.');
      return false;
    }

    if (formValues.password.length < 6) {
      setErrorMessage('Пароль должен содержать не менее 6 символов.');
      return false;
    }

    if (formValues.phone.length < 5) {
      setErrorMessage('Пожалуйста, введите корректный номер телефона.');
      return false;
    }

    return true;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');

    const isValid = validateForm();
    if (!isValid) {
      return;
    }

    const payload = {
      first_name: formValues.first_name,
      last_name: formValues.last_name,
      phone: formValues.phone,
      email: formValues.email || null,
      password: formValues.password,
    };

    if (formValues.referral_code) {
      payload.referral_code = formValues.referral_code;
    }

    const refCode = formValues.referral_code ? formValues.referral_code : null;

    setIsSubmitting(true);

    try {
      const data = await registerMember(payload, refCode);
      const { token, member } = data || {};

      if (token && member) {
        setSuccessMessage('Регистрация прошла успешно! Перенаправляем в профиль...');
        login(token, member);
        navigate('/profile');
        return;
      }

      if (member) {
        setSuccessMessage('Регистрация прошла успешно! Теперь войдите в систему.');
        navigate('/login', { state: { fromRegistration: true } });
        return;
      }

      setSuccessMessage('Регистрация прошла успешно!');
      navigate('/login');
    } catch (error) {
      console.error('Registration error', error);
      setErrorMessage('Произошла ошибка при регистрации. Пожалуйста, проверьте данные и попробуйте снова.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main
      data-easytag="id1-react/src/components/Auth/Register/index.jsx"
      className="page auth-page page-register"
    >
      <div className="container auth-container">
        <div className="card auth-card">
          <h1 className="auth-title">Регистрация</h1>
          <p className="auth-subtitle">
            Создайте аккаунт, чтобы получить персональную реферальную ссылку и
            отслеживать статистику по приглашённым клиентам.
          </p>

          <form className="auth-form" onSubmit={handleSubmit}>
            <div className="auth-form-row">
              <div className="auth-form-group">
                <label htmlFor="first_name" className="auth-label">
                  Имя<span className="auth-label-required">*</span>
                </label>
                <input
                  id="first_name"
                  name="first_name"
                  type="text"
                  className="auth-input"
                  placeholder="Иван"
                  value={formValues.first_name}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="auth-form-group">
                <label htmlFor="last_name" className="auth-label">
                  Фамилия<span className="auth-label-required">*</span>
                </label>
                <input
                  id="last_name"
                  name="last_name"
                  type="text"
                  className="auth-input"
                  placeholder="Иванов"
                  value={formValues.last_name}
                  onChange={handleChange}
                  required
                />
              </div>
            </div>

            <div className="auth-form-group">
              <label htmlFor="phone" className="auth-label">
                Номер телефона<span className="auth-label-required">*</span>
              </label>
              <input
                id="phone"
                name="phone"
                type="tel"
                className="auth-input"
                placeholder="Например, +7 900 000-00-00"
                value={formValues.phone}
                onChange={handleChange}
                required
              />
            </div>

            <div className="auth-form-group">
              <label htmlFor="email" className="auth-label">
                Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                className="auth-input"
                placeholder="name@example.com"
                value={formValues.email}
                onChange={handleChange}
              />
            </div>

            <div className="auth-form-group">
              <label htmlFor="password" className="auth-label">
                Пароль<span className="auth-label-required">*</span>
              </label>
              <input
                id="password"
                name="password"
                type="password"
                className="auth-input"
                placeholder="Минимум 6 символов"
                value={formValues.password}
                onChange={handleChange}
                required
                minLength={6}
              />
            </div>

            <div className="auth-form-group">
              <label htmlFor="referral_code" className="auth-label">
                Реферальный код (необязательно)
              </label>
              <input
                id="referral_code"
                name="referral_code"
                type="text"
                className="auth-input"
                placeholder="Введите код, если он у вас есть"
                value={formValues.referral_code}
                onChange={handleChange}
              />
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
                {isSubmitting ? 'Загрузка...' : 'Создать аккаунт'}
              </button>
            </div>

            <p className="auth-helper-text">
              Уже есть аккаунт?{' '}
              <button
                type="button"
                className="auth-link-button"
                onClick={() => navigate('/login')}
              >
                Войдите
              </button>
            </p>
          </form>
        </div>
      </div>
    </main>
  );
};

export default RegisterPage;
