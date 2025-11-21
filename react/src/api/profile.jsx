import instance from './axios';

/**
 * Получить профиль текущего пользователя (GET /api/auth/me/).
 * Возвращает расширенный объект Member с полями ранговой и финансовой системы.
 */
export async function getProfile() {
  const response = await instance.get('/api/auth/me/');
  return response.data ?? {};
}

/**
 * Получить агрегированную статистику профиля (GET /api/profile/stats/).
 */
export async function fetchProfileStats() {
  const response = await instance.get('/api/profile/stats/');
  return response.data ?? {};
}

/**
 * Обновить профиль текущего пользователя (PATCH /api/auth/me/).
 */
export async function updateProfile(data) {
  const response = await instance.patch('/api/auth/me/', data);
  return response.data ?? {};
}
