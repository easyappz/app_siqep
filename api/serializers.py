@@
 class LoginSerializer(serializers.Serializer):
     """Serializer used for login by phone and password."""
 
     phone = serializers.CharField()
     password = serializers.CharField(write_only=True)
 
+
+class ChangePasswordSerializer(serializers.Serializer):
+    """Serializer for changing password of the authenticated member."""
+
+    old_password = serializers.CharField(write_only=True)
+    new_password = serializers.CharField(write_only=True)
+
+    def validate_new_password(self, value: str) -> str:
+        if len(value) < 6:
+            raise serializers.ValidationError(
+                "Новый пароль должен содержать не менее 6 символов."
+            )
+        return value
+
+    def validate(self, attrs):
+        request = self.context.get("request")
+        member = getattr(request, "user", None) if request else None
+
+        if not isinstance(member, Member):
+            raise serializers.ValidationError(
+                "Не удалось определить текущего пользователя."
+            )
+
+        old_password = attrs.get("old_password")
+        if not member.check_password(old_password):
+            raise serializers.ValidationError(
+                {"old_password": "Текущий пароль указан неверно."}
+            )
+
+        return attrs
+
