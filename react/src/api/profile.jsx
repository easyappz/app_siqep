import instance from './axios';

export async function getProfile() {
  const response = await instance.get('/api/auth/me/');
  return response.data;
}

export async function fetchProfileStats() {
  const response = await instance.get('/api/profile/stats/');
  return response.data;
}

export async function updateProfile(data) {
  const response = await instance.patch('/api/auth/me/', data);
  return response.data;
}
