import instance from './axios';

/**
 * Get wallet summary for the current authenticated member (GET /api/wallet/summary/).
 */
export async function getWalletSummary() {
  const response = await instance.get('/api/wallet/summary/');
  return response.data ?? {};
}

/**
 * Get paginated wallet transactions for the current member (GET /api/wallet/transactions/).
 */
export async function getWalletTransactions(params = {}) {
  const response = await instance.get('/api/wallet/transactions/', { params });
  return response.data ?? [];
}

/**
 * Create an internal wallet deposit (POST /api/wallet/deposit/).
 */
export async function createWalletDeposit(data) {
  const response = await instance.post('/api/wallet/deposit/', data);
  return response.data ?? {};
}

/**
 * Spend funds from the wallet (POST /api/wallet/spend/).
 */
export async function createWalletSpend(data) {
  const response = await instance.post('/api/wallet/spend/', data);
  return response.data ?? {};
}
