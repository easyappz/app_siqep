import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import './index.css';
import App from './App';
import { AuthProvider } from './context/AuthContext';
import './api/axiosAuthInterceptor';
import './api/axiosLoginErrorInterceptor';

// Сохраняем реферальный код из URL (ref или referral_code) в localStorage
// до инициализации приложения, чтобы его можно было использовать на странице регистрации.
if (typeof window !== 'undefined') {
  try {
    const search = window.location.search;
    if (search) {
      const params = new URLSearchParams(search);
      const refFromUrl = params.get('ref') || params.get('referral_code');
      if (refFromUrl) {
        window.localStorage.setItem('referral_code', refFromUrl);
      }
    }
  } catch (error) {
    // Игнорируем ошибки работы с localStorage или URL
  }
}

const root = ReactDOM.createRoot(document.getElementById('root'));

root.render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
);
