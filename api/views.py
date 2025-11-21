diff --git a/api/views.py b/api/views.py
index 680dc79..ea0e934 100644
--- a/api/views.py
+++ b/api/views.py
@@ -47,6 +47,7 @@ from .serializers import (
     WalletAdminSpendSerializer,
     RankRuleSerializer,
 )
+from .referral_utils import process_member_deposit
 
 
 class HelloView(APIView):
@@ -267,6 +268,11 @@ class WalletDepositView(APIView):
                 meta={"source": "api_deposit"},
             )
         except ValueError as exc:
             raise ValidationError({"amount": [str(exc)]})
 
+        # Trigger referral activation and commissions for qualifying deposits
+        process_member_deposit(
+            member=member,
+            deposit_amount=amount,
+            created_at=tx.created_at,
+        )
+
         output = WalletTransactionSerializer(tx)
         return Response(output.data, status=status.HTTP_201_CREATED)
