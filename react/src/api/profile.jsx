import instance from './axios';

export async function fetchProfileStats() {
  const response = await instance.get('/api/profile/stats/');
  return response.data;
}
