import instance from './axios';

export async function getReferralTree(params = {}) {
  const response = await instance.get('/api/referrals/tree/', { params });
  return response.data;
}

export const fetchReferralTree = getReferralTree;

export const fetchReferralRewards = async (params = {}) => {
  const response = await instance.get('/api/referrals/rewards/', { params });
  return response.data;
};
