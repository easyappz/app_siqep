*** Begin Patch
*** Update File: api/views.py
@@
 from .serializers import (
     AdminMemberSerializer,
     AdminProfileSerializer,
     AdminReferralSerializer,
     AdminReferralStatsSerializer,
     AdminRequestStatusSerializer,
     AdminWalletSerializer,
+    ChangePasswordSerializer,
     DashboardSerializer,
@@
 class ChangePasswordView(APIView):
     permission_classes = (IsAuthenticated,)
 
     def post(self, request):
-        member = request.user.member
-        old_password = request.data.get("old_password")
-        new_password = request.data.get("new_password")
-
-        if not old_password or not new_password:
-            return Response(
-                {"detail": "Старый и новый пароли обязательны."},
-                status=status.HTTP_400_BAD_REQUEST,
-            )
-
-        if not request.user.check_password(old_password):
-            return Response(
-                {"detail": "Старый пароль указан неверно."},
-                status=status.HTTP_400_BAD_REQUEST,
-            )
-
-        if len(new_password) < 6:
-            return Response(
-                {"detail": "Новый пароль должен содержать минимум 6 символов."},
-                status=status.HTTP_400_BAD_REQUEST,
-            )
-
-        request.user.set_password(new_password)
-        request.user.save()
-
-        return Response(
-            {"detail": "Пароль успешно изменен."}, status=status.HTTP_200_OK
-        )
+        serializer = ChangePasswordSerializer(
+            data=request.data,
+            context={"request": request},
+        )
+        serializer.is_valid(raise_exception=True)
+        serializer.save()
+        return Response(
+            {"detail": "Пароль успешно изменен."},
+            status=status.HTTP_200_OK,
+        )
*** End Patch
