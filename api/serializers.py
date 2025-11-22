*** Begin Patch
*** Update File: api/serializers.py
@@
 class PasswordResetRequestSerializer(serializers.Serializer):
     email = serializers.EmailField()
+
+
+class ChangePasswordSerializer(serializers.Serializer):
+    MIN_PASSWORD_LENGTH = 6
+
+    old_password = serializers.CharField(
+        write_only=True,
+        style={"input_type": "password"},
+        error_messages={
+            "required": "Введите текущий пароль.",
+            "blank": "Введите текущий пароль.",
+        },
+    )
+    new_password = serializers.CharField(
+        write_only=True,
+        style={"input_type": "password"},
+        error_messages={
+            "required": "Введите новый пароль.",
+            "blank": "Введите новый пароль.",
+        },
+    )
+
+    def _get_user(self):
+        request = self.context.get("request")
+        if request is None:
+            return None
+        return getattr(request, "user", None)
+
+    def validate_old_password(self, value):
+        user = self._get_user()
+        if not user or not user.is_authenticated:
+            raise serializers.ValidationError("Не удалось определить пользователя.")
+        if not user.check_password(value):
+            raise serializers.ValidationError("Старый пароль указан неверно.")
+        return value
+
+    def validate_new_password(self, value):
+        if len(value) < self.MIN_PASSWORD_LENGTH:
+            raise serializers.ValidationError(
+                "Новый пароль должен содержать минимум 6 символов."
+            )
+        return value
+
+    def validate(self, attrs):
+        old_password = attrs.get("old_password")
+        new_password = attrs.get("new_password")
+        if old_password and new_password and old_password == new_password:
+            raise serializers.ValidationError(
+                {"new_password": ["Новый пароль должен отличаться от текущего."]}
+            )
+        return attrs
+
+    def save(self, **kwargs):
+        user = self._get_user()
+        if not user or not user.is_authenticated:
+            raise serializers.ValidationError("Не удалось определить пользователя.")
+        user.set_password(self.validated_data["new_password"])
+        user.save(update_fields=["password"])
+        return user
*** End Patch
