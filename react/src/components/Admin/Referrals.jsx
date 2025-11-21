diff --git a/react/src/components/Admin/Referrals.jsx b/react/src/components/Admin/Referrals.jsx
index 6d0b0d0..5a4b5a0 100644
--- a/react/src/components/Admin/Referrals.jsx
+++ b/react/src/components/Admin/Referrals.jsx
@@
-import React, { useEffect, useState } from 'react';
+import React, { useEffect, useMemo, useState } from 'react';
@@
 function getRankLabel(rank) {
   if (rank === 'silver') {
     return 'Серебряный';
   }
   if (rank === 'gold') {
@@
   }
   return 'Стандарт';
 }
+
+function formatStackCount(count) {
+  if (!count) {
+    return '';
+  }
+  if (count === 1) {
+    return '1 стек';
+  }
+  if (count >= 2 && count <= 4) {
+    return `${count} стека`;
+  }
+  return `${count} стеков`;
+}
+
+function formatCurrencyValue(amount) {
+  if (!Number.isFinite(amount) || amount <= 0) {
+    return '';
+  }
+  return new Intl.NumberFormat('ru-RU', {
+    minimumFractionDigits: 0,
+    maximumFractionDigits: 2,
+  }).format(amount);
+}
+
+function isReferralNodeActive(node) {
+  if (!node) {
+    return false;
+  }
+  if (node.status === 'active') {
+    return true;
+  }
+  if (node.status === 'pending') {
+    return false;
+  }
+  return Boolean(node.is_active_referral || node.has_paid_first_bonus);
+}
+
+function getReferralStatusLabel(node) {
+  return isReferralNodeActive(node) ? 'Активный' : 'Ожидает пополнения';
+}
+
+function formatReferralRewardValue(rewardSummary) {
+  if (!rewardSummary) {
+    return '—';
+  }
+  if (rewardSummary.money > 0) {
+    const formatted = formatCurrencyValue(rewardSummary.money);
+    if (formatted) {
+      return `${formatted} ₽`;
+    }
+  }
+  if (rewardSummary.stacks > 0) {
+    return formatStackCount(rewardSummary.stacks);
+  }
+  return '—';
+}
@@
   const memberRewardsList = Array.isArray(memberRewardsData?.rewards)
     ? memberRewardsData.rewards
     : Array.isArray(memberRewardsData?.items)
     ? memberRewardsData.items
     : Array.isArray(memberRewardsData)
     ? memberRewardsData
     : [];
+
+  const referralRewardsBySource = useMemo(() => {
+    return memberRewardsList.reduce((acc, reward) => {
+      const sourceId =
+        reward && (reward.source_member || reward.source_member_id || reward.source_memberId);
+      if (!sourceId) {
+        return acc;
+      }
+      const money = Number(reward.amount_rub) || 0;
+      const stacks = Number(reward.stack_count) || 0;
+      const current = acc[sourceId] || { money: 0, stacks: 0 };
+      current.money += money;
+      current.stacks += stacks;
+      acc[sourceId] = current;
+      return acc;
+    }, {});
+  }, [memberRewardsList]);
+
+  const memberActiveReferralsCount = useMemo(
+    () => memberTreeData.filter((node) => isReferralNodeActive(node)).length,
+    [memberTreeData],
+  );
+
+  const memberPendingReferralsCount = Math.max(
+    memberTreeData.length - memberActiveReferralsCount,
+    0,
+  );
@@
-    <main
-      data-easytag="id1-react/src/components/Admin/Referrals.jsx"
+    <main
+      data-easytag="id3-react/src/components/Admin/Referrals.jsx"
       className="page-admin-referrals-inner"
     >
@@
-                {!memberTreeLoading && !memberTreeError && (
-                  memberTreeData.length === 0 ? (
-                    <p className="admin-member-empty">
-                      У пользователя пока нет рефералов.
-                    </p>
-                  ) : (
-                    <div className="table-wrapper">
-                      <table className="table admin-table">
+                {!memberTreeLoading && !memberTreeError && (
+                  memberTreeData.length === 0 ? (
+                    <p className="admin-member-empty">
+                      У пользователя пока нет рефералов.
+                    </p>
+                  ) : (
+                    <>
+                      <div className="admin-member-summary-grid">
+                        <div className="admin-member-summary-card">
+                          <div className="admin-stat-title">Активные рефералы</div>
+                          <div className="admin-stat-value">{memberActiveReferralsCount}</div>
+                          <div className="admin-stat-caption">
+                            Игроки, которые пополнили баланс и активировали бонус.
+                          </div>
+                        </div>
+                        <div className="admin-member-summary-card">
+                          <div className="admin-stat-title">Ожидают пополнения</div>
+                          <div className="admin-stat-value">{memberPendingReferralsCount}</div>
+                          <div className="admin-stat-caption">
+                            Зарегистрированы, но ещё не совершили депозит.
+                          </div>
+                        </div>
+                      </div>
+                      <div className="table-wrapper">
+                        <table className="table admin-table">
                           <thead>
                             <tr>
                               <th>Пользователь</th>
                               <th>Тип</th>
                               <th>Ранг</th>
                               <th>Уровень</th>
-                              <th>Активность</th>
-                              <th>Бонус за первый турнир</th>
+                              <th>Статус</th>
+                              <th>Бонус за первый турнир</th>
+                              <th>Вознаграждение</th>
                             </tr>
                           </thead>
                           <tbody>
@@
-                            const isActive = Boolean(
-                              (node && node.is_active_referral) || (node && node.has_paid_first_bonus)
-                            );
-
                             const hasPaidFirstBonus = Boolean(node && node.has_paid_first_bonus);
+                            const statusLabel = getReferralStatusLabel(node);
+                            const rewardSummary =
+                              node && node.descendant_id
+                                ? referralRewardsBySource[node.descendant_id]
+                                : null;
+                            const rewardValue = formatReferralRewardValue(rewardSummary);
@@
-                                <td>{isActive ? 'Активный' : 'Неактивный'}</td>
-                                <td>{hasPaidFirstBonus ? 'Выплачен' : 'Не выплачен'}</td>
+                                <td>{statusLabel}</td>
+                                <td>{hasPaidFirstBonus ? 'Выплачен' : 'Не выплачен'}</td>
+                                <td>{rewardValue}</td>
                               </tr>
                             );
                           })}
-                      </table>
-                    </div>
-                  )
-                )}
+                        </table>
+                      </div>
+                    </>
+                  )
+                )}
