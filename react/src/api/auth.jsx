import instance from './axios';

export async function registerMember(data) {
  const response = await instance.post('/api/auth/register/', data);
  return response.data;
}

export async function loginMember(data) {
  // This call now receives either a normal axios response (2xx)
  // or, for /api/auth/login/ 400, the `response` object resolved by
  // axiosLoginErrorInterceptor instead of a rejected error.
  const response = await instance.post('/api/auth/login/', data);

  // If backend returned a non-success HTTP status, convert this into
  // a domain-level error without triggering the global axios error interceptor.
  if (response && typeof response.status === 'number' && response.status >= 400) {
    const error = new Error('Login failed');
    error.response = response;
    throw error;
  }

  return response.data;
}

export async function fetchCurrentMember() {
  const response = await instance.get('/api/auth/me/');
  return response.data;
}
