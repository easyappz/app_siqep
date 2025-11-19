import instance from './axios';

export async function registerMember(data) {
  const response = await instance.post('/api/auth/register/', data);
  return response.data;
}

export async function loginMember(data) {
  const response = await instance.post('/api/auth/login/', data);
  return response.data;
}

export async function fetchCurrentMember() {
  const response = await instance.get('/api/auth/me/');
  return response.data;
}
