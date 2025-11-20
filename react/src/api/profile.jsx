import instance from './axios';

/**
 * Получить профиль текущего пользователя.
 *
 * Эндпоинт: GET /api/auth/me/
 * Возвращает объект профиля (Member), включающий расширенные поля:
 * - total_deposits: строка с суммарной суммой депозитов в рублях;
 * - deposits: массив депозитов { id, amount, currency, is_test, created_at };
 * - total_influencer_earnings: строка с общей суммой заработка инфлюенсера в рублях;
 * а также остальные поля модели участника (имя, телефон, ранги, балансы и т.д.).
 */
export async function getProfile() {
  const response = await instance.get('/api/auth/me/');
  return response.data;
}

/**
 * Получить агрегированную статистику профиля (реферальная статистика, графики и т.п.).
 * Эндпоинт: GET /api/profile/stats/
 */
export async function fetchProfileStats() {
  const response = await instance.get('/api/profile/stats/');
  return response.data;
}

/**
 * Обновить профиль текущего пользователя (имя, фамилия, email, реквизиты вывода и т.п.).
 * Эндпоинт: PATCH /api/auth/me/
 */
export async function updateProfile(data) {
  const response = await instance.patch('/api/auth/me/', data);
  return response.data;
}
