"""
VisiPulse - نظام الإنذار المبكر وحوكمة البنية التحتية للمنشآت الصحية
نقطة تشغيل التطبيق الرئيسية (Entry Point)

التشغيل:
    streamlit run app.py
"""
from datetime import datetime

import streamlit as st

from database import init_db, get_session
from models import User, UserRole, PasswordHistory
from security import (
    verify_password, hash_password, validate_password_policy,
    PASSWORD_HISTORY_COUNT, SESSION_IDLE_MINUTES,
)
from auth import attempt_login, check_session_timeout, touch_session, logout
from audit import log_action

from ui import it_portal, executive_portal, employee_portal


st.set_page_config(
    page_title="VisiPulse | نظام الإنذار المبكر وحوكمة البنية التحتية",
    page_icon="🏥",
    layout="wide",
)

_RTL_CSS = """
<style>
html, body, [class*="css"] {
    direction: rtl;
    text-align: right;
    font-family: 'Segoe UI', 'Tahoma', sans-serif;
}
.stButton>button { direction: rtl; }
[data-testid="stMetricValue"], [data-testid="stMetricDelta"] { direction: ltr; }
section[data-testid="stSidebar"] { direction: rtl; text-align: right; }
div[data-testid="stForm"] { direction: rtl; text-align: right; }
</style>
"""
st.markdown(_RTL_CSS, unsafe_allow_html=True)

ROLE_LABELS = {"it": "تقنية المعلومات", "executive": "الإدارة العليا", "employee": "موظف"}


@st.cache_resource
def _bootstrap_db():
    """يُنشئ الجداول ويفعّل قيود سجل التدقيق مرة واحدة فقط عند إقلاع التطبيق."""
    init_db()
    return True


_bootstrap_db()


def _login_screen(session):
    st.markdown("## 🏥 VisiPulse")
    st.caption("نظام الإنذار المبكر وحوكمة البنية التحتية للمنشآت الصحية")
    st.divider()

    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        with st.form("login_form"):
            username = st.text_input("اسم المستخدم")
            password = st.text_input("كلمة المرور", type="password")
            submitted = st.form_submit_button("تسجيل الدخول", width="stretch")

        if submitted:
            user, result = attempt_login(session, username, password)
            if user is None:
                st.error(result)
            else:
                st.session_state.authenticated = True
                st.session_state.username = user.username
                st.session_state.user_id = user.id
                st.session_state.role = user.role.value
                st.session_state.must_change_password = bool(user.must_change_password or result == "expired")
                touch_session()
                st.rerun()


def _force_password_change_screen(session):
    st.warning("⚠️ يجب تغيير كلمة المرور قبل المتابعة (سياسة أمنية: أول تسجيل دخول أو انتهاء صلاحية دورية)")
    user = session.query(User).filter(User.id == st.session_state.get("user_id")).first()
    if not user:
        logout(session)
        st.rerun()
        return

    with st.form("change_password_form"):
        current_pwd = st.text_input("كلمة المرور الحالية", type="password")
        new_pwd = st.text_input("كلمة المرور الجديدة", type="password")
        confirm_pwd = st.text_input("تأكيد كلمة المرور الجديدة", type="password")
        submitted = st.form_submit_button("تحديث كلمة المرور")

    if not submitted:
        return

    if not verify_password(current_pwd, user.password_hash):
        st.error("كلمة المرور الحالية غير صحيحة")
        return
    if new_pwd != confirm_pwd:
        st.error("كلمتا المرور الجديدتان غير متطابقتين")
        return

    errors = validate_password_policy(new_pwd, user.username)
    if errors:
        for e in errors:
            st.error(e)
        return

    recent = (session.query(PasswordHistory)
              .filter(PasswordHistory.user_id == user.id)
              .order_by(PasswordHistory.created_at.desc())
              .limit(PASSWORD_HISTORY_COUNT).all())
    if verify_password(new_pwd, user.password_hash) or any(verify_password(new_pwd, h.password_hash) for h in recent):
        st.error(f"لا يمكن إعادة استخدام آخر {PASSWORD_HISTORY_COUNT} كلمات مرور مستخدمة سابقاً")
        return

    session.add(PasswordHistory(user_id=user.id, password_hash=user.password_hash))
    user.password_hash = hash_password(new_pwd)
    user.password_changed_at = datetime.utcnow()
    user.must_change_password = False
    session.commit()
    log_action(session, user.username, user.role.value, "تغيير كلمة المرور", "-", category="أمن")

    st.session_state.must_change_password = False
    st.success("تم تحديث كلمة المرور بنجاح")
    st.rerun()


def _sidebar(session, user):
    with st.sidebar:
        st.markdown(f"### 👋 {user.full_name}")
        st.caption(f"الدور: {ROLE_LABELS.get(user.role.value, user.role.value)}")
        st.caption(f"القسم: {user.department or '-'}")
        if user.last_login:
            st.caption(f"آخر دخول سابق: {user.last_login:%Y-%m-%d %H:%M}")
        st.divider()
        st.caption(f"⏱️ مهلة خمول الجلسة: {SESSION_IDLE_MINUTES} دقيقة")
        if st.button("🔒 تسجيل الخروج", width="stretch"):
            logout(session, user.username, user.role.value, "تسجيل خروج يدوي")
            st.rerun()


def main():
    session = get_session()

    if not st.session_state.get("authenticated"):
        _login_screen(session)
        return

    if check_session_timeout():
        stale_username = st.session_state.get("username")
        stale_role = st.session_state.get("role")
        logout(session, stale_username, stale_role, "انتهاء مهلة خمول الجلسة")
        st.warning("⏱️ انتهت الجلسة بسبب الخمول. الرجاء تسجيل الدخول مجدداً.")
        st.rerun()
        return

    touch_session()

    user = session.query(User).filter(User.id == st.session_state.get("user_id")).first()
    if not user or not user.is_active:
        logout(session)
        st.error("الحساب غير متاح حالياً. الرجاء التواصل مع إدارة تقنية المعلومات.")
        st.rerun()
        return

    _sidebar(session, user)

    if st.session_state.get("must_change_password"):
        _force_password_change_screen(session)
        return

    if user.role == UserRole.IT:
        it_portal.render(session, user)
    elif user.role == UserRole.EXECUTIVE:
        executive_portal.render(session, user)
    elif user.role == UserRole.EMPLOYEE:
        employee_portal.render(session, user)
    else:
        st.error("دور مستخدم غير معروف.")


if __name__ == "__main__":
    main()
