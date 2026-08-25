"""
VisiPulse - أداة توليد مفتاح التشفير (Fernet)
الاستخدام: python generate_key.py
يقوم بتوليد مفتاح تشفير آمن وإرشادت لتخزينه في ملف .env
"""
import os
from cryptography.fernet import Fernet

if __name__ == "__main__":
    key = Fernet.generate_key().decode()
    env_path = ".env"
    
    print("=" * 60)
    print("VisiPulse - مولد مفتاح التشفير الآمن")
    print("=" * 60)
    print("مفتاح التشفير الجديد (احفظه في مكان آمن ولا تقم بمشاركته):")
    print(f"\n{key}\n")
    print("=" * 60)
    
    # التحقق من وجود ملف .env مسبقاً لحماية البيانات الحالية
    if os.path.exists(env_path):
        print(f"[!] تنبيه: ملف '{env_path}' موجود مسبقاً.")
        choice = input("هل تريد إلحاق (أو تحديث) المفتاح تلقائياً في ملف .env؟ (y/N): ").strip().lower()
        if choice == 'y':
            # قراءة الملف الحالي لتجنب تكرار المتغير إن وجد
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            key_exists = False
            new_lines = []
            for line in lines:
                if line.startswith("ENCRYPTION_KEY="):
                    new_lines.append(f"ENCRYPTION_KEY={key}\n")
                    key_exists = True
                else:
                    new_lines.append(line)
            
            if not key_exists:
                new_lines.append(f"\nENCRYPTION_KEY={key}\n")
                
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            print(f"[+] تم تحديث ملف '{env_path}' بنجاح بمفتاح التشفير الجديد.")
        else:
            print(f"[*] يرجى نسخ السطر التالي يدوياً إلى ملف '{env_path}':")
            print(f"ENCRYPTION_KEY={key}")
    else:
        print(f"[*] لم يتم العثور على ملف '{env_path}'. يمكنك إنشاء الملف وإضافة السطر التالي:")
        print(f"ENCRYPTION_KEY={key}")
    print("=" * 60)
