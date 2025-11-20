import instance from './axios';

// Interceptor that converts expected 400 errors for the register endpoint
// into resolved responses, so the global interceptor in axios.js does not
// treat them as crashes.
instance.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    const hasResponse = Boolean(error && error.response);
    const hasConfig = Boolean(error && error.config);

    const status = hasResponse ? error.response.status : null;
    const url = hasConfig ? error.config.url : null;
    const isRegisterRequest = typeof url === 'string' && url.includes('/api/auth/register/');

    if (hasResponse && status === 400 && isRegisterRequest) {
      // Convert this specific axios rejection into a resolved response
      // so the global interceptor in axios.js does not log it as a crash.
      return Promise.resolve(error.response);
    }

    // For all other cases, keep the original rejection behavior
    return Promise.reject(error);
  }
);

export default instance;
