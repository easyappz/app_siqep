import instance from './axios';

instance.interceptors.request.use(
  (config) => {
    if (typeof window !== 'undefined') {
      const token = window.localStorage.getItem('memberToken');

      if (token) {
        // Ensure Authorization header is set for authenticated requests
        // eslint-disable-next-line no-param-reassign
        config.headers.Authorization = `Token ${token}`;
      }
    }

    return config;
  },
  (error) => Promise.reject(error)
);

export default instance;
