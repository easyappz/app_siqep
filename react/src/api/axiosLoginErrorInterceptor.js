import instance from './axios';

// This interceptor handles only expected 400 errors for the login endpoint
instance.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    const hasResponse = Boolean(error && error.response);
    const hasConfig = Boolean(error && error.config);

    const status = hasResponse ? error.response.status : null;
    const url = hasConfig ? error.config.url : null;
    const isLoginRequest = typeof url === 'string' && url.includes('/api/auth/login/');

    if (hasResponse && status === 400 && isLoginRequest) {
      // Convert this specific axios rejection into a resolved response
      // so the global interceptor in axios.js does not treat it as a crash.
      return Promise.resolve(error.response);
    }

    // For all other cases, keep the original rejection behavior
    return Promise.reject(error);
  }
);

export default instance;
