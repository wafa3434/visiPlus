"""
VisiPulse - أداة توليد مفتاح التشفير (Fernet)
الاستخدام: python generate_key.py
انسخ المفتاح الناتج إلى ملف .env ضمن المتغير ENCRYPTION_KEY
"""
from cryptography.fernet import Fernet

if __name__ == "__main__":
    key = Fernet.generate_key().decode()
    print("=" * 60)
    print("مفتاح التشفير الجديد (احتفظ به في مكان آمن ولا تشاركه):")
    print(key)
    print("=" * 60)
    print("أضِف السطر التالي إلى ملف .env:")
    print(f"ENCRYPTION_KEY={key}")
