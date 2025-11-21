import instance from './axios';

export async function fetchAdminMembers(params = {}) {
  const response = await instance.get('/api/admin/members/', { params });
  return response.data;
}

export async function createAdminMember(data) {
  const response = await instance.post('/api/admin/members/', data);
  return response.data;
}

export async function updateAdminMember(id, data) {
  const response = await instance.patch(`/api/admin/members/${id}/`, data);
  return response.data;
}

export async function fetchAdminReferrals(params = {}) {
  const response = await instance.get('/api/admin/referrals/', { params });
  return response.data;
}

export async function createAdminReferralEvent(data) {
  const response = await instance.post('/api/admin/referrals/', data);
  return response.data;
}

export async function fetchAdminStatsOverview() {
  const response = await instance.get('/api/admin/stats/overview/');
  return response.data;
}

export async function resetMemberPassword(memberId, data) {
  const payload = data && typeof data === 'object' ? data : {};
  const response = await instance.post(`/api/admin/members/${memberId}/reset-password/`, payload);
  return response.data;
}

export async function adminDebitWallet(data) {
  const payload = data && typeof data === 'object' ? data : {};
  const response = await instance.post('/api/admin/wallet/debit/', payload);
  return response.data;
}
