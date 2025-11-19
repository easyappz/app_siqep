import instance from './axios';

export async function registerMember(data, refCode) {
  let url = '/api/auth/register/';

  if (refCode) {
    const params = new URLSearchParams();
    params.set('ref', refCode);
    url = `${url}?${params.toString()}`;
  }

  const response = await instance.post(url, data);
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
