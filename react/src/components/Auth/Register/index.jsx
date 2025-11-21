import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { registerMember } from '../../../api/auth';
import { useAuth } from '../../../context/AuthContext';

const REFERRAL_CODE_STORAGE_KEY = 'referral_code';

const RegisterPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
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

  // При первом открытии страницы регистрации:
  // 1) читаем ref / referral_code из query-параметров и сохраняем в localStorage;
  // 2) если параметра в URL нет, подставляем значение из localStorage (если есть);
  // 3) автоматически подставляем код в форму, но не перетираем уже введённое пользователем.
  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    let codeFromUrl = '';

    if (location && location.search) {
      const params = new URLSearchParams(location.search);
      const refParam = params.get('ref') || params.get('referral_code');
      if (refParam) {
        codeFromUrl = refParam;
        try {
          window.localStorage.setItem(REFERRAL_CODE_STORAGE_KEY, refParam);
        } catch (storageError) {
          // ignore storage errors
        }
      }
    }

    if (!codeFromUrl) {
      try {
        const stored = window.localStorage.getItem(REFERRAL_CODE_STORAGE_KEY);
        if (stored) {
          codeFromUrl = stored;
        }
      } catch (storageError) {
        // ignore storage errors
      }
    }

    if (!codeFromUrl) {
      return;
    }

    setFormValues((prev) => {
      if (prev.referral_code) {
        return prev;
      }
      return {
        ...prev,
        referral_code: codeFromUrl,
      };
    });
  }, [location.search]);

  const handleChange = (event) => {
    const { name, value } = event.target;

    if (name === 'referral_code' && typeof window !== 'undefined') {
      try {
        if (value) {
          window.localStorage.setItem(REFERRAL_CODE_STORAGE_KEY, value);
        } else {
          window.localStorage.removeItem(REFERRAL_CODE_STORAGE_KEY);
        }
      } catch (storageError) {
        // ignore storage errors
      }
    }

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

    setIsSubmitting(true);

    try {
      const data = await registerMember(payload);
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

      const response = error && error.response ? error.response : null;
      const data = response && response.data ? response.data : null;

      if (data) {
        let message = '';

        const pickFirst = (value) => {
          if (Array.isArray(value) && value.length > 0) {
            return String(value[0]);
          }
          if (typeof value === 'string') {
            return value;
          }
          return '';
        };

        if (!message && Object.prototype.hasOwnProperty.call(data, 'phone')) {
          message = pickFirst(data.phone);
        }
        if (!message && Object.prototype.hasOwnProperty.call(data, 'email')) {
          message = pickFirst(data.email);
        }
        if (!message && Object.prototype.hasOwnProperty.call(data, 'referral_code')) {
          message = pickFirst(data.referral_code);
        }
        if (!message && Object.prototype.hasOwnProperty.call(data, 'non_field_errors')) {
          message = pickFirst(data.non_field_errors);
        }
        if (!message && Object.prototype.hasOwnProperty.call(data, 'detail')) {
          message = pickFirst(data.detail);
        }

        if (!message) {
          const values = Object.values(data);
          for (let i = 0; i < values.length; i += 1) {
            const candidate = pickFirst(values[i]);
            if (candidate) {
              message = candidate;
              break;
            }
          }
        }

        if (message) {
          setErrorMessage(message);
        } else {
          setErrorMessage('Произошла ошибка при регистрации. Пожалуйста, проверьте данные и попробуйте снова.');
        }
      } else {
        setErrorMessage('Произошла ошибка при регистрации. Пожалуйста, проверьте данные и попробуйте снова.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main
      data-easytag="id1-src/components/Auth/Register/index.jsx"
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
