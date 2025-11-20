import instance from './axios';

/**
 * Создать заявку на вывод средств для текущего пользователя.
 *
 * Эндпоинт: POST /api/withdrawal-requests/
 * Тело запроса: { amount: number, method: 'card' | 'crypto', destination: string }
 */
export async function createWithdrawalRequest(payload) {
  const response = await instance.post('/api/withdrawal-requests/', payload);
  return response.data;
}

/**
 * Получить список заявок на вывод средств текущего пользователя.
 *
 * Эндпоинт: GET /api/withdrawal-requests/
 */
export async function getMyWithdrawalRequests() {
  const response = await instance.get('/api/withdrawal-requests/');
  return response.data;
}
