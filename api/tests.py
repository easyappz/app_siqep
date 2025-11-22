*** Begin Patch
*** Update File: api/tests.py
@@
     def test_non_admin_cannot_list_wallet_transactions(self):
         self.client.force_authenticate(user=self.member_user)
         response = self.client.get(self.url, format="json")
         self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
+
+
+class ChangePasswordTests(APITestCase):
+    def setUp(self):
+        self.url = reverse("api:change-password")
+        self.old_password = "Oldpass123"
+        self.user = User.objects.create_user(
+            username="change-password-user",
+            email="changepassword@example.com",
+            password=self.old_password,
+        )
+
+    def test_change_password_success(self):
+        self.client.force_authenticate(user=self.user)
+        response = self.client.post(
+            self.url,
+            {"old_password": self.old_password, "new_password": "Newpass456"},
+            format="json",
+        )
+        self.assertEqual(response.status_code, status.HTTP_200_OK)
+        self.assertEqual(response.data["detail"], "Пароль успешно изменен.")
+        self.user.refresh_from_db()
+        self.assertTrue(self.user.check_password("Newpass456"))
+
+    def test_change_password_invalid_old_password(self):
+        self.client.force_authenticate(user=self.user)
+        response = self.client.post(
+            self.url,
+            {"old_password": "wrong-old", "new_password": "Newpass456"},
+            format="json",
+        )
+        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
+        self.assertIn("old_password", response.data)
+        self.assertIn("Старый пароль указан неверно.", response.data["old_password"][0])
+
+    def test_change_password_short_new_password(self):
+        self.client.force_authenticate(user=self.user)
+        response = self.client.post(
+            self.url,
+            {"old_password": self.old_password, "new_password": "short"},
+            format="json",
+        )
+        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
+        self.assertIn("new_password", response.data)
+        self.assertEqual(
+            response.data["new_password"][0],
+            "Новый пароль должен содержать минимум 6 символов.",
+        )
*** End Patch
