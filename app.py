from datetime import datetime
import random
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
    page_icon="logo.jpeg",
    layout="wide",
)

translations = {
    "ar": {
        "title": "VisiPulse - نظام الإنذار المبكر وحوكمة البنية التحتية",
        "subtitle": "نظام الإنذار المبكر وحوكمة البنية التحتية للمنشآت الصحية",
        "username": "اسم المستخدم",
        "password": "كلمة المرور",
        "login_btn": "تسجيل الدخول",
        "verify_title": "التحقق بخطوتين",
        "verify_msg": "تم إرسال رمز التحقق التجريبي إلى بريدك:",
        "code_input": "أدخل رمز التحقق المكون من أربعة أرقام",
        "verify_btn": "تأكيد الرمز",
        "invalid_code": "رمز التحقق غير صحيح، يرجى المحاولة مجدداً",
        "logout": "تسجيل الخروج",
        "role": "الدور",
        "department": "القسم",
        "last_login": "آخر دخول سابق",
        "idle_timeout": "مهلة خمول الجلسة",
    },
    "en": {
        "title": "VisiPulse - Predictive Hospital Monitor System",
        "subtitle": "Early Warning and Infrastructure Governance System for Healthcare Facilities",
        "username": "Username",
        "password": "Password",
        "login_btn": "Login",
        "verify_title": "Two-Step Verification",
        "verify_msg": "Demo verification code sent to your email:",
        "code_input": "Enter 4-digit verification code",
        "verify_btn": "Verify Code",
        "invalid_code": "Invalid verification code, please try again",
        "logout": "Logout",
        "role": "Role",
        "department": "Department",
        "last_login": "Last Login",
        "idle_timeout": "Session Idle Timeout",
    }
}

lang_choice = st.sidebar.selectbox("Language / اللغة", ["العربية", "English"])
current_lang = "ar" if lang_choice == "العربية" else "en"
t = translations[current_lang]

_RTL_CSS = f"""
<style>
html, body, [class*="css"] {{
    direction: {'rtl' if current_lang == 'ar' else 'ltr'};
    text-align: {'right' if current_lang == 'ar' else 'left'};
    font-family: 'Segoe UI', 'Tahoma', sans-serif;
}}
.stButton>button {{ direction: {'rtl' if current_lang == 'ar' else 'ltr'}; }}
[data-testid="stMetricValue"], [data-testid="stMetricDelta"] {{ direction: ltr; }}
section[data-testid="stSidebar"] {{ direction: {'rtl' if current_lang == 'ar' else 'ltr'}; text-align: {'right' if current_lang == 'ar' else 'left'}; }}
div[data-testid="stForm"] {{ direction: {'rtl' if current_lang == 'ar' else 'ltr'}; text-align: {'right' if current_lang == 'ar' else 'left'}; }}

/* توسيط حاوية الشعار الرئيسي وتحسين جودته */
.stImage {{
    display: flex;
    justify-content: center;
    align-items: center;
    margin-left: auto;
    margin-right: auto;
}}

img {{
    image-rendering: -webkit-optimize-contrast;
    image-rendering: crisp-edges;
}}
</style>
"""
st.markdown(_RTL_CSS, unsafe_allow_html=True)

ROLE_LABELS = {"it": "تقنية المعلومات", "executive": "الإدارة العليا", "employee": "موظف"}

@st.cache_resource
def _bootstrap_db():
    init_db()
    return True

_bootstrap_db()


def _login_screen(session):
    # استخدام الأعمدة لتوسيط الشعار والعناوين بالمنتصف تماماً بدقة
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        try:
            st.image("logo.jpeg", width=180)
        except Exception:
            pass
        st.markdown(f"<h3 style='text-align: center;'>{t['title']}</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; color: gray;'>{t['subtitle']}</p>", unsafe_allow_html=True)
            
    st.divider()

    if st.session_state.get("pending_verification"):
        _, mid_v, _ = st.columns([1, 1.2, 1])
        with mid_v:
            st.info(f"{t['verify_msg']} **{st.session_state.get('demo_code')}**")
            with st.form("verify_form"):
                entered_code = st.text_input(t["code_input"], type="password")
                verify_submitted = st.form_submit_button(t["verify_btn"], width="stretch")

            if verify_submitted:
                if entered_code == str(st.session_state.get("demo_code")):
                    st.session_state.authenticated = True
                    st.session_state.pending_verification = False
                    st.success("تم التحقق بنجاح")
                    st.rerun()
                else:
                    st.error(t["invalid_code"])
        return

    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        with st.form("login_form"):
            username = st.text_input(t["username"])
            password = st.text_input(t["password"], type="password")
            submitted = st.form_submit_button(t["login_btn"], width="stretch")

        if submitted:
            user, result = attempt_login(session, username, password)
            if user is None:
                st.error(result)
            else:
                code = random.randint(1000, 9999)
                st.session_state.demo_code = code
                st.session_state.pending_verification = True
                st.session_state.temp_user_id = user.id
                st.session_state.temp_username = user.username
                st.session_state.temp_role = user.role.value
                st.rerun()


def _force_password_change_screen(session):
    st.warning("يجب تغيير كلمة المرور قبل المتابعة وفقاً للسياسة الأمنية للنظام")
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
        st.markdown(f"### {user.full_name}")
        st.caption(f"{t['role']}: {ROLE_LABELS.get(user.role.value, user.role.value)}")
        st.caption(f"{t['department']}: {user.department or '-'}")
        if user.last_login:
            st.caption(f"{t['last_login']}: {user.last_login:%Y-%m-%d %H:%M}")
        st.divider()
        st.caption(f"{t['idle_timeout']}: {SESSION_IDLE_MINUTES} min")
        if st.button(t['logout'], width="stretch"):
            logout(session, user.username, user.role.value, "تسجيل خروج يدوي")
            st.rerun()


def main():
    session = get_session()

    if not st.session_state.get("authenticated") or st.session_state.get("pending_verification"):
        if st.session_state.get("pending_verification") and not st.session_state.get("user_id"):
            st.session_state.user_id = st.session_state.get("temp_user_id")
            st.session_state.username = st.session_state.get("temp_username")
            st.session_state.role = st.session_state.get("temp_role")
        
        _login_screen(session)
        return

    if check_session_timeout():
        stale_username = st.session_state.get("username")
        stale_role = st.session_state.get("role")
        logout(session, stale_username, stale_role, "انتهاء مهلة خمول الجلسة")
        st.warning("انتهت الجلسة بسبب الخمول. يرجى تسجيل الدخول مجدداً.")
        st.rerun()
        return

    touch_session()

    user = session.query(User).filter(User.id == st.session_state.get("user_id")).first()
    if not user or not user.is_active:
        logout(session)
        st.error("الحساب غير متاح حالياً. يرجى التواصل مع إدارة تقنية المعلومات.")
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
