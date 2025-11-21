import instance from './axios';

// New helper: get admin members list with search and pagination
export async function getAdminMembers(options = {}) {
  const params = {};

  if (options && typeof options === 'object') {
    const { searchPhone, search_phone, page, pageSize, page_size } = options;

    const resolvedSearchPhone = typeof search_phone !== 'undefined' ? search_phone : searchPhone;
    const resolvedPageSize = typeof page_size !== 'undefined' ? page_size : pageSize;

    if (resolvedSearchPhone !== undefined && resolvedSearchPhone !== null && resolvedSearchPhone !== '') {
      params.search_phone = resolvedSearchPhone;
    }

    if (page !== undefined && page !== null) {
      params.page = page;
    }

    if (resolvedPageSize !== undefined && resolvedPageSize !== null) {
      params.page_size = resolvedPageSize;
    }
  }

  const response = await instance.get('/api/admin/members/', { params });
  return response.data;
}

// Backward compatible helper (older name) that simply delegates to getAdminMembers
export async function fetchAdminMembers(params = {}) {
  return getAdminMembers(params);
}

export async function createAdminMember(data) {
  const response = await instance.post('/api/admin/members/', data);
  return response.data;
}

export async function updateAdminMember(id, data) {
  const response = await instance.patch(`/api/admin/members/${id}/`, data);
  return response.data;
}

// New helper: get detailed info about a single member
export async function getAdminMemberDetail(memberId) {
  const response = await instance.get(`/api/admin/members/${memberId}/`);
  return response.data;
}

// New helper: adjust member balance (cash and/or V-Coins)
export async function adjustAdminMemberBalance(memberId, payload) {
  const body = payload && typeof payload === 'object' ? payload : {};
  const response = await instance.post(
    `/api/admin/members/${memberId}/adjust-balance/`,
    body
  );
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
  const response = await instance.post(
    `/api/admin/members/${memberId}/reset-password/`,
    payload
  );
  return response.data;
}

export async function adminDebitWallet(data) {
  const payload = data && typeof data === 'object' ? data : {};
  const response = await instance.post('/api/admin/wallet/debit/', payload);
  return response.data;
}

export async function adminDepositWallet(data) {
  const payload = data && typeof data === 'object' ? data : {};
  const response = await instance.post('/api/admin/wallet/deposit/', payload);
  return response.data;
}

export async function adminSpendWallet(data) {
  const payload = data && typeof data === 'object' ? data : {};
  const response = await instance.post('/api/admin/wallet/spend/', payload);
  return response.data;
}
