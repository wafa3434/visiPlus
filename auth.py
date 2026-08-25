"""
VisiPulse - وحدة المصادقة وإدارة الجلسة (Authentication & Session Management)

التحديثات:
- استخدام التوقيت المعياري الحديث datetime.now(timezone.utc) بدلاً من datetime.utcnow()
  لتجنب تحذيرات الإهمال (Deprecation Warnings) وضمان التوافق مع باقي الوحدات (مثل Audit.py).
"""
from datetime import datetime, timedelta, timezone

import streamlit as st

from models import User
from security import (
    verify_password, MAX_FAILED_ATTEMPTS, LOCKOUT_MINUTES,
    SESSION_IDLE_MINUTES, PASSWORD_EXPIRY_DAYS,
)
from audit import log_action


def attempt_login(session, username: str, password: str):
    """
    يحاول تسجيل الدخول مع تطبيق آلية القفل المؤقت للحساب.
    يعيد Tuple: (user أو None, حالة/رسالة).
    عند النجاح: (user, 'ok') أو (user, 'expired') إذا انتهت صلاحية كلمة المرور.
    عند الفشل: (None, "رسالة الخطأ المعروضة للمستخدم").
    """
    username = (username or "").strip()
    user = session.query(User).filter(User.username == username).first()

    current_time = datetime.now(timezone.utc)

    if not user or not user.is_active:
        log_action(session, username or "-", "-", "محاولة دخول فاشلة",
                   "اسم مستخدم غير موجود أو حساب غير مُفعّل", category="أمن", severity="warning")
        return None, "اسم المستخدم أو كلمة المرور غير صحيحة"

    if user.locked_until and user.locked_until > current_time:
        remaining = max(1, int((user.locked_until - current_time).total_seconds() // 60) + 1)
        log_action(session, username, user.role.value, "محاولة دخول أثناء قفل الحساب",
                   f"متبقٍ نحو {remaining} دقيقة على فك القفل", category="أمن", severity="warning")
        return None, f"الحساب مقفل مؤقتاً بسبب تجاوز عدد محاولات الدخول الخاطئة. حاول مرة أخرى بعد {remaining} دقيقة"

    if not verify_password(password, user.password_hash):
        user.failed_attempts = (user.failed_attempts or 0) + 1
        severity = "warning"
        if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = current_time + timedelta(minutes=LOCKOUT_MINUTES)
            severity = "critical"
        session.commit()
        log_action(session, username, user.role.value, "محاولة دخول فاشلة",
                   f"كلمة مرور خاطئة (المحاولة رقم {user.failed_attempts} من {MAX_FAILED_ATTEMPTS})",
                   category="أمن", severity=severity)
        return None, "اسم المستخدم أو كلمة المرور غير صحيحة"

    # نجاح تسجيل الدخول
    user.failed_attempts = 0
    user.locked_until = None
    user.last_login = current_time
    session.commit()
    log_action(session, username, user.role.value, "تسجيل دخول ناجح", "-", category="أمن")

    expired = (current_time - user.password_changed_at).days > PASSWORD_EXPIRY_DAYS
    return user, ("expired" if expired else "ok")


def check_session_timeout() -> bool:
    """يتحقق مما إذا كانت الجلسة قد تجاوزت مهلة الخمول المسموحة."""
    last = st.session_state.get("last_activity")
    if not last:
        return False
    return datetime.now(timezone.utc) - last > timedelta(minutes=SESSION_IDLE_MINUTES)


def touch_session():
    """يُحدّث طابع آخر نشاط للجلسة (يُستدعى في كل تفاعل ناجح للمستخدم)."""
    st.session_state.last_activity = datetime.now(timezone.utc)


def logout(session=None, username: str = None, role: str = None, reason: str = "تسجيل خروج يدوي"):
    """يُنهي الجلسة الحالية ويسجّل الحدث في سجل التدقيق."""
    if session is not None and username:
        log_action(session, username, role or "-", "تسجيل خروج", reason, category="أمن")
    for key in list(st.session_state.keys()):
        del st.session_state[key]
