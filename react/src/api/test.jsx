import instance from './axios';

/**
 * Test-only API helper to simulate demo deposits for Amir and Alfirа (Амир и Альфира).
 *
 * Sends a POST request to /api/test/simulate_demo_deposits/.
 * The auth header is attached automatically via axiosAuthInterceptor.
 *
 * @param {number} [amount] Optional custom deposit amount in RUB for each member.
 * @returns {Promise<any>} Parsed response data from the backend.
 */
export const simulateDemoDeposits = async (amount) => {
  const payload = {};

  if (typeof amount === 'number' && Number.isFinite(amount) && amount > 0) {
    payload.amount = amount;
  }

  const response = await instance.post('/api/test/simulate_demo_deposits/', payload);
  return response.data;
};

export default simulateDemoDeposits;
