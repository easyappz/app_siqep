import instance from './axios';

/**
 * Retrieve the referral tree for the current member (or specified member_id).
 * Response in OpenAPI is an array of ReferralNode objects, but some
 * downstream utilities may still wrap data under a `nodes` field. This helper
 * always returns a flat array so UI code can rely on it.
 */
export async function getReferralTree(params = {}) {
  const response = await instance.get('/api/referrals/tree/', { params });
  const data = response.data;

  if (Array.isArray(data)) {
    return data;
  }

  if (data && Array.isArray(data.nodes)) {
    return data.nodes;
  }

  return [];
}

export const fetchReferralTree = getReferralTree;

/**
 * Retrieve referral rewards along with their summary block.
 * Always returns an object with `rewards` (array) and `summary` (object)
 * so consumers can safely destructure the response regardless of backend shape.
 */
export async function fetchReferralRewards(params = {}) {
  const response = await instance.get('/api/referrals/rewards/', { params });
  const raw = response.data || {};

  const rewards = Array.isArray(raw.rewards)
    ? raw.rewards
    : Array.isArray(raw.results)
    ? raw.results
    : Array.isArray(raw)
    ? raw
    : [];

  const summary = {
    total_stack_count: raw.summary?.total_stack_count ?? 0,
    total_influencer_amount: raw.summary?.total_influencer_amount ?? '0.00',
    total_first_tournament_amount: raw.summary?.total_first_tournament_amount ?? '0.00',
    total_deposit_percent_amount: raw.summary?.total_deposit_percent_amount ?? '0.00',
  };

  return { rewards, summary };
}

/**
 * List referral bonuses earned from wallet spend events of referrals.
 */
export async function getReferralBonuses() {
  const response = await instance.get('/api/referrals/bonuses/');
  const data = response.data;

  if (Array.isArray(data)) {
    return data;
  }

  if (Array.isArray(data?.results)) {
    return data.results;
  }

  return [];
}

/**
 * List deposits made by direct referrals of the current member.
 */
export async function getReferralDeposits() {
  const response = await instance.get('/api/referrals/deposits/');
  const data = response.data;

  if (Array.isArray(data)) {
    return data;
  }

  if (Array.isArray(data?.results)) {
    return data.results;
  }

  return [];
}
