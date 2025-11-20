import instance from './axios';

/**
 * Test-only API helper to simulate deposits for Amir and Alfirа.
 *
 * When called, it sends a POST request to /api/test/simulate-deposits/.
 * The MemberToken-based auth header is attached automatically via
 * axiosAuthInterceptor.
 *
 * @param {number} [amount] Optional custom deposit amount in RUB for each member.
 * @returns {Promise<any>} Parsed response data from the backend.
 */
export const simulateAmirAlfiraDeposits = async (amount) => {
  const payload = {};

  if (typeof amount === 'number' && Number.isFinite(amount) && amount > 0) {
    payload.amount = Math.floor(amount);
  }

  const response = await instance.post('/api/test/simulate-deposits/', payload);
  return response.data;
};

export default simulateAmirAlfiraDeposits;
