"""
VisiPulse - وحدة الأمن والحوكمة (Security & Governance Module)
- تجزئة كلمات المرور (bcrypt)
- سياسة كلمة مرور صارمة متوافقة مع متطلبات الهيئة الوطنية للأمن السيبراني (NCA ECC)
- تشفير الحقول الحساسة (Fernet) بالاعتماد على مفتاح من متغيرات البيئة (.env)
- إعدادات القفل المؤقت للحساب ومهلة خمول الجلسة (تُقرأ من .env)
"""
import os
import re
from datetime import datetime

import bcrypt
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()


# ============================================================
# التشفير - Fernet (تشفير متماثل معتمد على مفتاح البيئة)
import os
import streamlit as st

# دعم قراءة مفتاح التشفير من Streamlit Secrets أو من النظام المحلي
try:
    ENCRYPTION_KEY = st.secrets["VISIPULSE_ENCRYPTION_KEY"]
except (KeyError, FileNotFoundError):
    ENCRYPTION_KEY = os.getenv("VISIPULSE_ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    raise RuntimeError("خطأ حرج: لم يتم العثور على مفتاح التشفير VISIPULSE_ENCRYPTION_KEY.")

def encrypt_field(value):
    """يشفّر قيمة نصية حساسة (بريد إلكتروني، هاتف، عنوان IP...) قبل تخزينها."""
    if value is None or value == "":
        return None
    return _fernet.encrypt(str(value).encode("utf-8")).decode("utf-8")


def decrypt_field(value) -> str:
    """يفك تشفير قيمة مخزّنة. يعيد نصاً واضحاً عند الفشل بدلاً من رفع استثناء يُعطّل الواجهة."""
    if not value:
        return ""
    try:
        return _fernet.decrypt(value.encode("utf-8")).decode("utf-8")
    except Exception:
        return "[تعذر فك التشفير]"


# ============================================================
# إعدادات الأمان القابلة للضبط عبر .env
# ============================================================
MAX_FAILED_ATTEMPTS = int(os.getenv("MAX_FAILED_ATTEMPTS", "5"))
LOCKOUT_MINUTES = int(os.getenv("LOCKOUT_MINUTES", "15"))
SESSION_IDLE_MINUTES = int(os.getenv("SESSION_IDLE_MINUTES", "15"))
PASSWORD_HISTORY_COUNT = int(os.getenv("PASSWORD_HISTORY_COUNT", "4"))
PASSWORD_EXPIRY_DAYS = int(os.getenv("PASSWORD_EXPIRY_DAYS", "90"))

_COMMON_WEAK_PASSWORDS = {
    "password", "12345678", "123456789", "qwerty123", "p@ssw0rd",
    "admin123", "welcome1", "changeme", "hospital123", "healthcare1",
}


# ============================================================
# تجزئة والتحقق من كلمات المرور (bcrypt)
# ============================================================
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    if not password or not hashed:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def validate_password_policy(password: str, username: str = ""):
    """
    يتحقق من مطابقة كلمة المرور لسياسة أمن المعلومات (متوافقة مع متطلبات NCA ECC):
    - 12 حرفاً على الأقل
    - حرف كبير + حرف صغير + رقم + رمز خاص
    - عدم احتواء اسم المستخدم
    - عدم كونها من كلمات المرور الشائعة
    يعيد قائمة رسائل الأخطاء (قائمة فارغة تعني أن كلمة المرور مطابقة للسياسة).
    """
    password = password or ""
    errors = []

    if len(password) < 12:
        errors.append("يجب ألا تقل كلمة المرور عن 12 حرفاً")
    if not re.search(r"[A-Z]", password):
        errors.append("يجب أن تحتوي على حرف إنجليزي كبير واحد على الأقل (A-Z)")
    if not re.search(r"[a-z]", password):
        errors.append("يجب أن تحتوي على حرف إنجليزي صغير واحد على الأقل (a-z)")
    if not re.search(r"[0-9]", password):
        errors.append("يجب أن تحتوي على رقم واحد على الأقل")
    if not re.search(r"""[!@#$%^&*()\-_=+\[\]{};:'",.<>/?\\|`~]""", password):
        errors.append("يجب أن تحتوي على رمز خاص واحد على الأقل (!@#$%...)")
    if username and username.lower() in password.lower():
        errors.append("لا يجوز أن تحتوي كلمة المرور على اسم المستخدم")
    if password.lower() in _COMMON_WEAK_PASSWORDS:
        errors.append("كلمة المرور شائعة/ضعيفة جداً، يرجى اختيار كلمة مرور أقوى")

    return errors


def days_since(dt: datetime) -> int:
    return (datetime.utcnow() - dt).days
