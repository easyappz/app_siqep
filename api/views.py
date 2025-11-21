diff --git a/api/views.py b/api/views.py
index 9efcbb8..a817d98 100644
--- a/api/views.py
+++ b/api/views.py
@@ -292,6 +292,11 @@ class WalletDepositView(APIView):
             )
         except ValueError as exc:
             raise ValidationError({"amount": [str(exc)]})
 
+        process_member_deposit(
+            member=member,
+            deposit_amount=amount,
+        )
+
         output = WalletTransactionSerializer(tx)
         return Response(output.data, status=status.HTTP_201_CREATED)
 