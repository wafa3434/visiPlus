"""
VisiPulse - بوابة تقنية المعلومات (IT Portal)
تضم: الصحة الإلكترونية | الدعم الفني | البنية التحتية والشبكات | الأنظمة والتطبيقات
     | سجل التدقيق الأمني | إدارة المستخدمين (مضافة لدعم تشغيل RBAC فعلياً)
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from models import Ticket, Alert, SystemAsset, AuditLog, User, UserRole
from security import encrypt_field, decrypt_field, hash_password, validate_password_policy
from audit import log_action, verify_chain

PRIORITY_ICONS = {"حرجة": "🔴", "عالية": "🟠", "متوسطة": "🟡", "منخفضة": "🟢"}
ROLE_LABELS = {"it": "تقنية المعلومات", "executive": "الإدارة العليا", "employee": "موظف"}


def render(session, user):
    st.title("🖥️ بوابة تقنية المعلومات")
    st.caption(f"مرحباً {user.full_name} | القسم: {user.department or '-'}")

    tabs = st.tabs([
        "🩺 الصحة الإلكترونية",
        "🛠️ الدعم الفني",
        "🌐 البنية التحتية والشبكات",
        "💻 الأنظمة والتطبيقات",
        "🔒 سجل التدقيق الأمني",
        "👥 إدارة المستخدمين",
    ])

    with tabs[0]:
        _render_ehealth(session)
    with tabs[1]:
        _render_support(session, user)
    with tabs[2]:
        _render_infrastructure(session, user)
    with tabs[3]:
        _render_systems(session, user)
    with tabs[4]:
        _render_audit(session)
    with tabs[5]:
        _render_user_management(session, user)


# ---------------------------------------------------------------- E-Health
def _render_ehealth(session):
    st.subheader("حالة أنظمة الصحة الإلكترونية")
    assets = session.query(SystemAsset).filter(SystemAsset.department == "الصحة الإلكترونية").all()
    if assets:
        cols = st.columns(min(len(assets), 4))
        for i, a in enumerate(assets):
            with cols[i % len(cols)]:
                st.metric(a.name, a.status, delta=a.criticality)
    else:
        st.info("لا توجد أنظمة صحة إلكترونية مسجلة بعد. يمكن إضافتها من تبويب «الأنظمة والتطبيقات».")

    st.divider()
    st.subheader("إنذارات متعلقة بالصحة الإلكترونية")
    alerts = (session.query(Alert)
              .filter(Alert.department.in_(["الصحة الإلكترونية", "تقنية المعلومات"]))
              .order_by(Alert.created_at.desc()).all())
    _alerts_table(alerts)


# ---------------------------------------------------------------- Technical Support
def _render_support(session, user):
    st.subheader("طابور بلاغات الدعم الفني")
    status_filter = st.multiselect("تصفية حسب الحالة", ["مفتوحة", "قيد المعالجة", "مغلقة"],
                                    default=["مفتوحة", "قيد المعالجة"], key="it_ticket_status_filter")
    tickets = (session.query(Ticket).filter(Ticket.status.in_(status_filter))
               .order_by(Ticket.created_at.desc()).all()) if status_filter else []

    if not tickets:
        st.info("لا توجد بلاغات مطابقة للتصفية الحالية.")

    for t in tickets:
        with st.expander(f"{PRIORITY_ICONS.get(t.priority, '')} [{t.ticket_number}] {t.title} — {t.status}"):
            st.write(f"**الوصف:** {t.description or '-'}")
            st.write(f"**التصنيف:** {t.category} | **الموقع:** {t.location or '-'}")
            st.write(f"**مقدّم البلاغ:** {t.created_by} | **تاريخ الإنشاء:** {t.created_at:%Y-%m-%d %H:%M}")
            c1, c2, c3 = st.columns(3)
            with c1:
                new_status = st.selectbox("تحديث الحالة", ["مفتوحة", "قيد المعالجة", "مغلقة"],
                                           index=["مفتوحة", "قيد المعالجة", "مغلقة"].index(t.status),
                                           key=f"status_{t.id}")
            with c2:
                assignee = st.text_input("إسناد إلى", value=t.assigned_to or "", key=f"assign_{t.id}")
            with c3:
                notes = st.text_input("ملاحظات الحل", value=t.resolution_notes or "", key=f"notes_{t.id}")
            if st.button("💾 حفظ التحديث", key=f"save_{t.id}"):
                old_status = t.status
                t.status = new_status
                t.assigned_to = assignee or None
                t.resolution_notes = notes or None
                t.updated_at = datetime.utcnow()
                if new_status == "مغلقة" and old_status != "مغلقة":
                    t.resolved_at = datetime.utcnow()
                session.commit()
                log_action(session, user.username, user.role.value, "تحديث بلاغ",
                           f"{t.ticket_number}: {old_status} -> {new_status}", category="دعم فني")
                st.success("تم حفظ التحديث")
                st.rerun()

    st.divider()
    st.subheader("إنشاء بلاغ داخلي")
    with st.form("it_new_ticket"):
        title = st.text_input("العنوان")
        desc = st.text_area("الوصف")
        category = st.selectbox("التصنيف", ["الصحة الإلكترونية", "البنية التحتية", "الأنظمة والتطبيقات", "عام"])
        priority = st.selectbox("الأولوية", ["حرجة", "عالية", "متوسطة", "منخفضة"])
        location = st.text_input("الموقع")
        if st.form_submit_button("إنشاء البلاغ"):
            if not title.strip():
                st.error("العنوان مطلوب")
            else:
                count = session.query(Ticket).count() + 1
                ticket = Ticket(ticket_number=f"TCK-{count:04d}", title=title, description=desc,
                                 category=category, priority=priority, location=location,
                                 created_by=user.username, status="مفتوحة")
                session.add(ticket)
                session.commit()
                log_action(session, user.username, user.role.value, "إنشاء بلاغ",
                           f"{ticket.ticket_number}: {title}", category="دعم فني")
                st.success(f"تم إنشاء البلاغ {ticket.ticket_number}")
                st.rerun()


# ---------------------------------------------------------------- Infrastructure
def _render_infrastructure(session, user):
    st.subheader("جرد البنية التحتية والشبكات")
    assets = session.query(SystemAsset).filter(SystemAsset.asset_type.in_(["خادم", "جهاز شبكة"])).all()
    rows = [{
        "الاسم": a.name, "النوع": a.asset_type, "القسم": a.department,
        "الحالة": a.status, "الأهمية": a.criticality,
        "عنوان IP": decrypt_field(a.ip_enc), "المسؤول": a.owner,
    } for a in assets]
    if rows:
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    else:
        st.info("لا توجد أصول بنية تحتية مسجلة بعد.")

    with st.expander("➕ إضافة أصل جديد"):
        with st.form("new_infra_asset"):
            name = st.text_input("اسم الأصل")
            asset_type = st.selectbox("النوع", ["خادم", "جهاز شبكة"])
            department = st.text_input("القسم", value="البنية التحتية")
            ip = st.text_input("عنوان IP")
            criticality = st.selectbox("الأهمية", ["حرجة", "عالية", "متوسطة", "منخفضة"])
            if st.form_submit_button("إضافة"):
                if not name.strip():
                    st.error("اسم الأصل مطلوب")
                else:
                    asset = SystemAsset(name=name, asset_type=asset_type, department=department,
                                         ip_enc=encrypt_field(ip), status="يعمل", criticality=criticality,
                                         owner=user.username)
                    session.add(asset)
                    session.commit()
                    log_action(session, user.username, user.role.value, "إضافة أصل بنية تحتية",
                               name, category="بنية تحتية")
                    st.success("تمت الإضافة")
                    st.rerun()

    st.divider()
    st.subheader("إنذارات البنية التحتية والشبكات")
    alerts = (session.query(Alert)
              .filter(Alert.department.in_(["البنية التحتية", "تقنية المعلومات", "العناية المركزة"]))
              .order_by(Alert.created_at.desc()).all())
    _alerts_table(alerts)


# ---------------------------------------------------------------- Systems & Apps
def _render_systems(session, user):
    st.subheader("جرد الأنظمة والتطبيقات")
    assets = session.query(SystemAsset).filter(SystemAsset.asset_type == "تطبيق").all()
    rows = [{"التطبيق": a.name, "القسم": a.department, "الحالة": a.status,
             "الأهمية": a.criticality, "المسؤول": a.owner} for a in assets]
    if rows:
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    else:
        st.info("لا توجد تطبيقات مسجلة بعد.")

    with st.expander("➕ تسجيل تطبيق / نظام جديد"):
        with st.form("new_app_asset"):
            name = st.text_input("اسم التطبيق")
            department = st.text_input("القسم المالك", value="الأنظمة والتطبيقات")
            ip = st.text_input("عنوان IP / نقطة الوصول")
            criticality = st.selectbox("الأهمية", ["حرجة", "عالية", "متوسطة", "منخفضة"], key="app_crit")
            if st.form_submit_button("تسجيل"):
                if not name.strip():
                    st.error("اسم التطبيق مطلوب")
                else:
                    asset = SystemAsset(name=name, asset_type="تطبيق", department=department,
                                         ip_enc=encrypt_field(ip), status="يعمل", criticality=criticality,
                                         owner=user.username)
                    session.add(asset)
                    session.commit()
                    log_action(session, user.username, user.role.value, "تسجيل تطبيق", name, category="أنظمة")
                    st.success("تم التسجيل")
                    st.rerun()


# ---------------------------------------------------------------- Audit Log
def _render_audit(session):
    st.subheader("سجل التدقيق الأمني (غير قابل للتعديل)")
    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button("🔍 التحقق من سلامة السجل"):
            ok, bad_id = verify_chain(session)
            if ok:
                st.success("سلسلة السجل سليمة ولم يتم اكتشاف أي تلاعب ✅")
            else:
                st.error(f"⚠️ تم اكتشاف عدم تطابق عند السجل رقم {bad_id} — قد يشير ذلك إلى محاولة تلاعب")
    with c2:
        st.caption("يعتمد السجل على سلسلة تجزئات SHA-256 (Hash Chain) مع قيود قاعدة بيانات "
                   "تمنع تعديل أو حذف السجلات نهائياً.")

    severity_filter = st.multiselect("تصفية حسب الخطورة", ["info", "warning", "critical"],
                                      default=["info", "warning", "critical"])
    logs = (session.query(AuditLog).filter(AuditLog.severity.in_(severity_filter))
            .order_by(AuditLog.timestamp.desc()).limit(500).all()) if severity_filter else []

    rows = [{"الوقت": l.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "المستخدم": l.username,
             "الدور": ROLE_LABELS.get(l.role, l.role), "الحدث": l.action, "الفئة": l.category,
             "الخطورة": l.severity, "التفاصيل": l.details} for l in logs]
    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch", hide_index=True, height=420)
    if not df.empty:
        st.download_button("⬇️ تصدير CSV", df.to_csv(index=False).encode("utf-8-sig"),
                            file_name="audit_log_export.csv", mime="text/csv")


# ---------------------------------------------------------------- User Management
def _render_user_management(session, user):
    st.subheader("إدارة حسابات المستخدمين")
    users = session.query(User).all()
    rows = [{"اسم المستخدم": u.username, "الاسم": u.full_name, "الدور": ROLE_LABELS.get(u.role.value, u.role.value),
             "القسم": u.department, "نشط": "نعم" if u.is_active else "لا",
             "مقفل حتى": u.locked_until.strftime("%Y-%m-%d %H:%M") if u.locked_until else "-",
             "آخر دخول": u.last_login.strftime("%Y-%m-%d %H:%M") if u.last_login else "-"} for u in users]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    st.divider()
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**➕ إنشاء حساب جديد**")
        with st.form("create_user_form"):
            username = st.text_input("اسم المستخدم (بالإنجليزية)")
            full_name = st.text_input("الاسم الكامل")
            role = st.selectbox("الدور", [r.value for r in UserRole], format_func=lambda r: ROLE_LABELS[r])
            department = st.text_input("القسم")
            email = st.text_input("البريد الإلكتروني")
            phone = st.text_input("رقم الجوال")
            temp_password = st.text_input("كلمة مرور مؤقتة", type="password",
                                           help="سيُطلب من المستخدم تغييرها عند أول تسجيل دخول")
            if st.form_submit_button("إنشاء الحساب"):
                errors = validate_password_policy(temp_password, username)
                if not username.strip() or not full_name.strip():
                    st.error("اسم المستخدم والاسم الكامل حقول مطلوبة")
                elif session.query(User).filter(User.username == username).first():
                    st.error("اسم المستخدم مستخدم بالفعل")
                elif errors:
                    for e in errors:
                        st.error(e)
                else:
                    new_user = User(username=username, full_name=full_name, role=UserRole(role),
                                     department=department, password_hash=hash_password(temp_password),
                                     must_change_password=True,
                                     email_enc=encrypt_field(email), phone_enc=encrypt_field(phone))
                    session.add(new_user)
                    session.commit()
                    log_action(session, user.username, user.role.value, "إنشاء مستخدم", username,
                               category="إدارة مستخدمين", severity="warning")
                    st.success(f"تم إنشاء الحساب {username} بنجاح")
                    st.rerun()

    with c2:
        st.markdown("**🔧 إجراءات على حساب قائم**")
        usernames = [u.username for u in users]
        if usernames:
            target_username = st.selectbox("اختر المستخدم", usernames, key="manage_target")
            target = session.query(User).filter(User.username == target_username).first()
            if target:
                cc1, cc2, cc3 = st.columns(3)
                with cc1:
                    if st.button("🔓 فك القفل", disabled=not target.locked_until):
                        target.locked_until = None
                        target.failed_attempts = 0
                        session.commit()
                        log_action(session, user.username, user.role.value, "فك قفل حساب", target_username,
                                   category="إدارة مستخدمين", severity="warning")
                        st.success("تم فك القفل")
                        st.rerun()
                with cc2:
                    toggle_label = "إلغاء التفعيل" if target.is_active else "تفعيل"
                    if st.button(toggle_label):
                        target.is_active = not target.is_active
                        session.commit()
                        log_action(session, user.username, user.role.value, "تغيير حالة تفعيل حساب",
                                   f"{target_username}: {'مفعل' if target.is_active else 'معطل'}",
                                   category="إدارة مستخدمين", severity="warning")
                        st.success("تم التحديث")
                        st.rerun()
                with cc3:
                    if st.button("🔁 إجبار تغيير كلمة المرور"):
                        target.must_change_password = True
                        session.commit()
                        log_action(session, user.username, user.role.value, "إجبار تغيير كلمة مرور",
                                   target_username, category="إدارة مستخدمين", severity="warning")
                        st.success("سيُطلب من المستخدم تغيير كلمة المرور في الدخول القادم")
                        st.rerun()


def _alerts_table(alerts):
    if not alerts:
        st.info("لا توجد إنذارات في هذا القسم حالياً.")
        return
    rows = [{"الخطورة": f"{PRIORITY_ICONS.get(a.severity, '')} {a.severity}", "العنوان": a.title,
             "الوصف": a.description, "الحالة": a.status,
             "التاريخ": a.created_at.strftime("%Y-%m-%d %H:%M")} for a in alerts]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
