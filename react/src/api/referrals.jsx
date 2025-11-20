import instance from './axios';

export const fetchReferralTree = async (params = {}) => {
  const response = await instance.get('/api/referrals/tree/', { params });
  return response.data;
};

export const fetchReferralRewards = async (params = {}) => {
  const response = await instance.get('/api/referrals/rewards/', { params });
  return response.data;
};
