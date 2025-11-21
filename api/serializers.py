diff --git a/api/serializers.py b/api/serializers.py
index 7cb954e..ce9a178 100644
--- a/api/serializers.py
+++ b/api/serializers.py
@@
     def validate_email(self, value: str) -> str:
-        """Ensure email is уникаль...
+        """Ensure email is unique and raise a Russian ValidationError if already used."""
 
         if not value:
             return value
 
         if Member.objects.filter(email=value).exists():
