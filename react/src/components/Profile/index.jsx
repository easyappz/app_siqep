diff --git a/react/src/components/Profile/index.jsx b/react/src/components/Profile/index.jsx
index 9ef8a9e..f4a3f1c 100644
--- a/react/src/components/Profile/index.jsx
+++ b/react/src/components/Profile/index.jsx
@@
-import React, { useCallback, useContext, useEffect, useState } from 'react';
+import React, { useCallback, useContext, useEffect, useMemo, useState } from 'react';
@@
 function getInfluencerRewardDescription(rankLabel, currentRankRule) {
   const multiplier = currentRankRule
     ? Number(currentRankRule.influencer_depth_bonus_multiplier || 1)
     : 1;
@@
   return [
     `Ваш текущий ранг: ${rankLabel}.`,
     `За прямого реферала (уровень 1) вы получаете ${baseDirect} ₽ за его первый турнир.`,
     `За рефералов на уровнях 2–10 вы получаете глубинный кэшбэк: ${depthBonusText} за первый турнир каждого нового игрока в цепочке (множитель относительно базовых 50 ₽ зависит от ранга).`,
     'Дополнительно вы всегда получаете 10% со всех дальнейших депозитов каждого вашего прямого реферала на фишки, независимо от ранга.',
   ];
 }
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
+function getReferralStatusTitle(node) {
+  return isReferralNodeActive(node) ? 'Активный' : 'Ожидает пополнения';
+}
+
+function aggregateRewardsBySource(rewards) {
+  if (!Array.isArray(rewards)) {
+    return {};
+  }
+  return rewards.reduce((acc, reward) => {
+    const sourceId =
+      reward && (reward.source_member || reward.source_member_id || reward.source_memberId);
+    if (!sourceId) {
+      return acc;
+    }
+    const money = Number(reward.amount_rub) || 0;
+    const stacks = Number(reward.stack_count) || 0;
+    const current = acc[sourceId] || { money: 0, stacks: 0 };
+    current.money += money;
+    current.stacks += stacks;
+    acc[sourceId] = current;
+    return acc;
+  }, {});
+}
@@
   const formatRewardDateTime = (isoValue) => {
     if (!isoValue) {
       return '—';
     }
@@
       return isoValue;
     }
   };
+
+  const formatCurrencyValue = (amount) => {
+    if (!Number.isFinite(amount) || amount <= 0) {
+      return '';
+    }
+    return new Intl.NumberFormat('ru-RU', {
+      minimumFractionDigits: 0,
+      maximumFractionDigits: 2,
+    }).format(amount);
+  };
 
   const formatStackText = (count) => {
     if (!count) {
       return '';
     }
@@
     }
 
     return `${count} стеков`;
   };
+
+  const formatReferralRewardDisplay = (rewardSummary) => {
+    if (!rewardSummary) {
+      return '—';
+    }
+    if (rewardSummary.money > 0) {
+      const formatted = formatCurrencyValue(rewardSummary.money);
+      if (formatted) {
+        return `${formatted} ₽`;
+      }
+    }
+    if (rewardSummary.stacks > 0) {
+      return formatStackText(rewardSummary.stacks);
+    }
+    return '—';
+  };
@@
   const rewardsList = Array.isArray(rewardsData?.rewards)
     ? rewardsData.rewards
     : Array.isArray(rewardsData?.items)
     ? rewardsData.items
     : Array.isArray(rewardsData)
     ? rewardsData
     : [];
+
+  const referralRewardsBySource = useMemo(
+    () => aggregateRewardsBySource(rewardsList),
+    [rewardsList],
+  );
+
+  const treeActiveReferralsCount = useMemo(
+    () => treeData.filter((node) => isReferralNodeActive(node)).length,
+    [treeData],
+  );
+
+  const treePendingReferralsCount = Math.max(
+    treeData.length - treeActiveReferralsCount,
+    0,
+  );
@@
-    <main
-      data-easytag="id1-src/components/Profile/index.jsx"
+    <main
+      data-easytag="id4-react/src/components/Profile/index.jsx"
       className="page page-profile"
     >
@@
           {!isLoadingTree && !treeError && (
             treeData.length === 0 ? (
               <div className="profile-tree-empty">
                 У вас пока нет рефералов. Поделитесь реферальной ссылкой, чтобы начать
                 строить структуру.
               </div>
             ) : (
-              <div className="profile-tree-table-wrapper">
-                <table className="profile-tree-table">
+              <>
+                <div className="profile-rewards-summary-grid">
+                  <div className="profile-rewards-summary-card">
+                    <div className="profile-stat-label">Активные рефералы</div>
+                    <div className="profile-stat-value">{treeActiveReferralsCount}</div>
+                    <div className="profile-stat-caption">
+                      Уже пополнили баланс и принесли вам бонусы.
+                    </div>
+                  </div>
+
+                  <div className="profile-rewards-summary-card">
+                    <div className="profile-stat-label">Ожидают пополнения</div>
+                    <div className="profile-stat-value">{treePendingReferralsCount}</div>
+                    <div className="profile-stat-caption">
+                      Зарегистрировались, но ещё не совершили депозит.
+                    </div>
+                  </div>
+                </div>
+
+                <div className="profile-tree-table-wrapper">
+                  <table className="profile-tree-table">
                     <thead>
                       <tr>
                         <th>Пользователь</th>
                         <th>Тип</th>
                         <th>Ранг</th>
                         <th>Уровень</th>
-                        <th>Статус</th>
+                        <th>Статус</th>
+                        <th>Вознаграждение</th>
                       </tr>
                     </thead>
                     <tbody>
                       {treeData.map((node, index) => {
@@
-                      const isActive = Boolean(
-                        (node && node.is_active_referral) || (node && node.has_paid_first_bonus)
-                      );
+                      const statusLabel = getReferralStatusTitle(node);
+                      const rewardSummary =
+                        node && node.descendant_id
+                          ? referralRewardsBySource[node.descendant_id]
+                          : null;
+                      const rewardValue = formatReferralRewardDisplay(rewardSummary);
 
                       return (
                         <tr key={node.descendant_id || index}>
                           <td>{displayName}</td>
                           <td>{nodeTypeLabel}</td>
                           <td>{nodeRankLabel}</td>
                           <td>{level}</td>
-                          <td>{isActive ? 'Активный реферал' : 'Неактивный'}</td>
+                          <td>{statusLabel}</td>
+                          <td>{rewardValue}</td>
                         </tr>
                       );
                     })}
-                </table>
-              </div>
+                  </table>
+                </div>
+              </>
             )
           )}
         </section>
