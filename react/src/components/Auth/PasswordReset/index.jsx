import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { requestPasswordReset, confirmPasswordReset } from '../../../api/auth';

const PasswordResetPage = () => {
  const navigate = useNavigate();

  const [step, setStep] = useState(1);

  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');

  const [isRequestSubmitting, setIsRequestSubmitting] = useState(false);
  const [isConfirmSubmitting, setIsConfirmSubmitting] = useState(false);

  const [requestMessage, setRequestMessage] = useState('');
  const [confirmMessage, setConfirmMessage] = useState('');

  const [devCode, setDevCode] = useState('');

  const [errors, setErrors] = useState({});

  const clearErrors = () => {
    setErrors({});
  };

  const handleRequestSubmit = async (event) => {
    event.preventDefault();
    clearErrors();
    setRequestMessage('');
    setConfirmMessage('');

    const emailTrimmed = email ? email.trim() : '';
    const phoneTrimmed = phone ? phone.trim() : '';

    if (!emailTrimmed && !phoneTrimmed) {
      setErrors({
        non_field_errors: 'Укажите email или номер телефона.',
      });
      return;
    }

    setIsRequestSubmitting(true);

    try {
      const payload = {
        email: emailTrimmed || null,
        phone: phoneTrimmed || null,
      };

      const data = await requestPasswordReset(payload);

      const detailMessage = data && data.detail ? data.detail : 'Код отправлен. Проверьте сообщения.';
      setRequestMessage(detailMessage);

      if (data && data.dev_code) {
        setDevCode(String(data.dev_code));
      } else {
        setDevCode('');
      }

      setStep(2);
    } catch (error) {
      const responseData = error && error.response && error.response.data ? error.response.data : null;
      const nextErrors = {};

      if (responseData) {
        if (responseData.email) {
          const value = Array.isArray(responseData.email) ? responseData.email[0] : responseData.email;
          nextErrors.email = String(value);
        }
        if (responseData.phone) {
          const value = Array.isArray(responseData.phone) ? responseData.phone[0] : responseData.phone;
          nextErrors.phone = String(value);
        }
        if (responseData.non_field_errors) {
          const value = Array.isArray(responseData.non_field_errors)
            ? responseData.non_field_errors[0]
            : responseData.non_field_errors;
          nextErrors.non_field_errors = String(value);
        }
        if (!nextErrors.non_field_errors && typeof responseData.detail === 'string') {
          nextErrors.non_field_errors = responseData.detail;
        }
      } else {
        nextErrors.non_field_errors = 'Не удалось отправить код. Попробуйте ещё раз.';
      }

      setErrors(nextErrors);
    } finally {
      setIsRequestSubmitting(false);
    }
  };

  const handleConfirmSubmit = async (event) => {
    event.preventDefault();
    clearErrors();
    setConfirmMessage('');

    const emailTrimmed = email ? email.trim() : '';
    const phoneTrimmed = phone ? phone.trim() : '';

    if (!emailTrimmed && !phoneTrimmed) {
      setErrors({
        non_field_errors: 'Укажите email или номер телефона.',
      });
      return;
    }

    if (!code) {
      setErrors({ code: 'Введите код, полученный по SMS или email.' });
      return;
    }

    if (!newPassword) {
      setErrors({ new_password: 'Введите новый пароль.' });
      return;
    }

    setIsConfirmSubmitting(true);

    try {
      const payload = {
        email: emailTrimmed || null,
        phone: phoneTrimmed || null,
        code,
        new_password: newPassword,
      };

      const data = await confirmPasswordReset(payload);
      const detailMessage = data && data.detail ? data.detail : 'Пароль успешно сброшен. Теперь вы можете войти.';

      setConfirmMessage(detailMessage);
    } catch (error) {
      const responseData = error && error.response && error.response.data ? error.response.data : null;
      const nextErrors = {};

      if (responseData) {
        if (responseData.email) {
          const value = Array.isArray(responseData.email) ? responseData.email[0] : responseData.email;
          nextErrors.email = String(value);
        }
        if (responseData.phone) {
          const value = Array.isArray(responseData.phone) ? responseData.phone[0] : responseData.phone;
          nextErrors.phone = String(value);
        }
        if (responseData.code) {
          const value = Array.isArray(responseData.code) ? responseData.code[0] : responseData.code;
          nextErrors.code = String(value);
        }
        if (responseData.new_password) {
          const value = Array.isArray(responseData.new_password)
            ? responseData.new_password[0]
            : responseData.new_password;
          nextErrors.new_password = String(value);
        }
        if (responseData.non_field_errors) {
          const value = Array.isArray(responseData.non_field_errors)
            ? responseData.non_field_errors[0]
            : responseData.non_field_errors;
          nextErrors.non_field_errors = String(value);
        }
        if (!nextErrors.non_field_errors && typeof responseData.detail === 'string') {
          nextErrors.non_field_errors = responseData.detail;
        }
      } else {
        nextErrors.non_field_errors = 'Не удалось сбросить пароль. Попробуйте ещё раз.';
      }

      setErrors(nextErrors);
    } finally {
      setIsConfirmSubmitting(false);
    }
  };

  const handleGoToLogin = () => {
    navigate('/login');
  };

  return (
    <main
      data-easytag="id1-react/src/components/Auth/PasswordReset/index.jsx"
      className="page auth-page page-password-reset"
    >
      <div className="container auth-container">
        <div className="card auth-card">
          <h1 className="auth-title">Восстановление пароля</h1>
          <p className="auth-subtitle">
            Если вы забыли пароль, запросите одноразовый код, а затем задайте новый пароль.
          </p>

          {step === 1 && (
            <form className="auth-form" onSubmit={handleRequestSubmit}>
              <div className="auth-form-group">
                <label htmlFor="email" className="auth-label">
                  Email (при наличии)
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  className="auth-input"
                  placeholder="name@example.com"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
                {errors.email && (
                  <div className="auth-message auth-message-error">{errors.email}</div>
                )}
              </div>

              <div className="auth-form-group">
                <label htmlFor="phone" className="auth-label">
                  Номер телефона (альтернатива email)
                </label>
                <input
                  id="phone"
                  name="phone"
                  type="tel"
                  className="auth-input"
                  placeholder="Например, +7 900 000-00-00"
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                />
                {errors.phone && (
                  <div className="auth-message auth-message-error">{errors.phone}</div>
                )}
              </div>

              {errors.non_field_errors && (
                <div className="auth-message auth-message-error">
                  {errors.non_field_errors}
                </div>
              )}

              {requestMessage && (
                <div className="auth-message auth-message-success">{requestMessage}</div>
              )}

              {devCode && (
                <div className="auth-message auth-message-info">
                  <strong>Код для тестирования:</strong> {devCode}
                  <div>Этот код показывается только в режиме разработки, чтобы упростить тестирование.</div>
                </div>
              )}

              <div className="auth-form-footer">
                <button
                  type="submit"
                  className="btn btn-primary auth-submit-btn"
                  disabled={isRequestSubmitting}
                >
                  {isRequestSubmitting ? 'Отправка...' : 'Отправить код'}
                </button>
              </div>

              <p className="auth-helper-text">
                Вспомнили пароль?{' '}
                <Link to="/login" className="auth-link">
                  Вернуться к входу
                </Link>
              </p>
            </form>
          )}

          {step === 2 && (
            <form className="auth-form" onSubmit={handleConfirmSubmit}>
              <div className="auth-form-group">
                <label htmlFor="email-confirm" className="auth-label">
                  Email (если указывали на первом шаге)
                </label>
                <input
                  id="email-confirm"
                  name="email-confirm"
                  type="email"
                  className="auth-input"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
                {errors.email && (
                  <div className="auth-message auth-message-error">{errors.email}</div>
                )}
              </div>

              <div className="auth-form-group">
                <label htmlFor="phone-confirm" className="auth-label">
                  Номер телефона (если использовали его)
                </label>
                <input
                  id="phone-confirm"
                  name="phone-confirm"
                  type="tel"
                  className="auth-input"
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                />
                {errors.phone && (
                  <div className="auth-message auth-message-error">{errors.phone}</div>
                )}
              </div>

              <div className="auth-form-group">
                <label htmlFor="code" className="auth-label">
                  Код подтверждения
                </label>
                <input
                  id="code"
                  name="code"
                  type="text"
                  className="auth-input"
                  placeholder="Введите код из SMS или письма"
                  value={code}
                  onChange={(event) => setCode(event.target.value)}
                />
                {errors.code && (
                  <div className="auth-message auth-message-error">{errors.code}</div>
                )}
              </div>

              <div className="auth-form-group">
                <label htmlFor="new_password" className="auth-label">
                  Новый пароль
                </label>
                <input
                  id="new_password"
                  name="new_password"
                  type="password"
                  className="auth-input"
                  placeholder="Минимум 6 символов"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                />
                {errors.new_password && (
                  <div className="auth-message auth-message-error">
                    {errors.new_password}
                  </div>
                )}
              </div>

              {errors.non_field_errors && (
                <div className="auth-message auth-message-error">
                  {errors.non_field_errors}
                </div>
              )}

              {confirmMessage && (
                <div className="auth-message auth-message-success">{confirmMessage}</div>
              )}

              <div className="auth-form-footer auth-form-footer-space-between">
                <button
                  type="button"
                  className="btn btn-secondary auth-submit-btn"
                  onClick={() => setStep(1)}
                  disabled={isConfirmSubmitting}
                >
                  Назад
                </button>

                <button
                  type="submit"
                  className="btn btn-primary auth-submit-btn"
                  disabled={isConfirmSubmitting}
                >
                  {isConfirmSubmitting ? 'Сброс...' : 'Сбросить пароль'}
                </button>
              </div>

              <p className="auth-helper-text">
                Готово?{' '}
                <button
                  type="button"
                  className="auth-link-button"
                  onClick={handleGoToLogin}
                >
                  Перейти к входу
                </button>
              </p>
            </form>
          )}
        </div>
      </div>
    </main>
  );
};

export default PasswordResetPage;
