import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'institute_django.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()
try:
    u = User.objects.get(username='admin')
    u.set_password('123456')
    u.save()
    print("Password set for admin")
except Exception as e:
    print(f"Error: {e}")
