diff --git a/react/src/api/referrals.jsx b/react/src/api/referrals.jsx
index 8f1c8d9..d0c6458 100644
--- a/react/src/api/referrals.jsx
+++ b/react/src/api/referrals.jsx
@@
-import instance from './axios';
-
-export async function getReferralTree(params = {}) {
-  const response = await instance.get('/api/referrals/tree/', { params });
-  return response.data;
-}
-
-export const fetchReferralTree = getReferralTree;
-
-export const fetchReferralRewards = async (params = {}) => {
-  const response = await instance.get('/api/referrals/rewards/', { params });
-  return response.data;
-};
+import instance from './axios';
+
+/**
+ * @typedef {Object} ReferralNode
+ * @property {number} descendant_id
+ * @property {number} level
+ * @property {boolean} has_paid_first_bonus
+ * @property {string} username
+ * @property {'player' | 'influencer'} user_type
+ * @property {'standard' | 'silver' | 'gold' | 'platinum'} rank
+ * @property {boolean} is_active_referral
+ * @property {'active' | 'pending'} [status]
+ */
+
+/**
+ * Fetch the referral tree for the current member or, for admins, a selected member.
+ *
+ * @param {Object} params
+ * @param {number} [params.member_id] Optional member id (admin only).
+ * @returns {Promise<ReferralNode[] | { nodes: ReferralNode[] }>}
+ */
+export async function getReferralTree(params = {}) {
+  const response = await instance.get('/api/referrals/tree/', { params });
+  return response.data;
+}
+
+/**
+ * Legacy alias kept for backwards compatibility.
+ */
+export const fetchReferralTree = getReferralTree;
+
+/**
+ * @typedef {Object} ReferralRewardEntry
+ * @property {number} id
+ * @property {'PLAYER_STACK' | 'INFLUENCER_FIRST_TOURNAMENT' | 'INFLUENCER_DEPOSIT_PERCENT'} reward_type
+ * @property {string | number} amount_rub
+ * @property {string | number} stack_count
+ * @property {number} depth
+ * @property {string} created_at
+ * @property {number} source_member
+ * @property {string} source_member_name
+ */
+
+/**
+ * Fetch referral reward entries together with the aggregated summary block.
+ *
+ * @param {Object} params
+ * @param {number} [params.member_id] Optional member id (admin only).
+ * @returns {Promise<{ rewards: ReferralRewardEntry[], summary: Object }>}
+ */
+export const fetchReferralRewards = async (params = {}) => {
+  const response = await instance.get('/api/referrals/rewards/', { params });
+  return response.data;
+};
