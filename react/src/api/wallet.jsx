import instance from './axios';

/**
 * Get wallet summary for the current authenticated member.
 *
 * Endpoint: GET /api/wallet/summary/
 * Response: WalletSummary (balance, total_deposited, total_spent).
 */
export async function getWalletSummary() {
  const response = await instance.get('/api/wallet/summary/');
  return response.data;
}

/**
 * Get paginated wallet transactions for the current authenticated member.
 *
 * Endpoint: GET /api/wallet/transactions/
 * Optional params: { page, page_size, type, ... } passed as query params.
 */
export async function getWalletTransactions(params = {}) {
  const response = await instance.get('/api/wallet/transactions/', { params });
  return response.data;
}

/**
 * Create an internal/app-level wallet deposit for the current member.
 *
 * Endpoint: POST /api/wallet/deposit/
 * Body: { amount: string | number, description?: string }
 */
export async function createWalletDeposit(data) {
  const response = await instance.post('/api/wallet/deposit/', data);
  return response.data;
}

/**
 * Spend funds from the current member's wallet.
 *
 * Endpoint: POST /api/wallet/spend/
 * Body: { amount: string | number, description?: string, category?: string }
 */
export async function createWalletSpend(data) {
  const response = await instance.post('/api/wallet/spend/', data);
  return response.data;
}
