"""
VisiPulse - بوابة تقنية المعلومات (IT Portal) المحدثة
تضم: الصحة الإلكترونية | مدير قسم الجودة | الأنظمة والتطبيقات | الدعم الفني المتقدم | البنية التحتية
     | سجل التدقيق الأمني | إدارة المستخدمين
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from models import Ticket, Alert, SystemAsset, AuditLog, User, UserRole, KPI
from security import encrypt_field, decrypt_field, hash_password, validate_password_policy
from audit import log_action, verify_chain

PRIORITY_LABELS = {"حرجة": "حرج", "عالية": "عالي", "متوسطة": "متوسط", "منخفضة": "منخفض"}
ROLE_LABELS = {"it": "تقنية المعلومات", "executive": "الإدارة العليا", "employee": "موظف"}


def render(session, user):
    st.title("بوابة تقنية المعلومات")
    st.caption(f"مرحباً {user.full_name} | القسم: {user.department or '-'}")

    tabs = st.tabs([
        "لوحة أقسام تقنية المعلومات",
        "طابور وصيانة الدعم الفني",
        "سجل التدقيق الأمني",
        "إدارة المستخدمين",
    ])

    with tabs[0]:
        _render_it_sub_sections(session, user)
    with tabs[1]:
        _render_support_advanced(session, user)
    with tabs[2]:
        _render_audit(session)
    with tabs[3]:
        _render_user_management(session, user)


# ---------------------------------------------------------------- أقسام وتخصصات الـ IT
def _render_it_sub_sections(session, user):
    st.subheader("التخصصات والمهام الاستباقية لإدارة تقنية المعلومات")
    
    selected_section = st.selectbox(
        "اختر القسم / الإدارة الفرعية:",
        [
            "مدير الصحة الإلكترونية",
            "مدير قسم الجودة",
            "الأنظمة والتطبيقات",
            "البنية التحتية والشبكات"
        ],
        key="it_sub_section_selector"
    )

    st.divider()

    if "الصحة الإلكترونية" in selected_section:
        st.markdown("### مدير الصحة الإلكترونية - المهام الاستباقية")
        st.info("متابعة استمرارية أنظمة ملفات المرضى الإلكترونية والتأكد من عدم وجود أي تباطؤ يؤثر على جودة الرعاية الطبية.")
        
        assets = session.query(SystemAsset).filter(SystemAsset.department == "الصحة الإلكترونية").all()
        if assets:
            cols = st.columns(min(len(assets), 3))
            for i, a in enumerate(assets):
                with cols[i % len(cols)]:
                    st.metric(a.name, a.status, delta=f"الأهمية: {a.criticality}")
        else:
            st.warning("لا توجد أنظمة صحة إلكترونية مسجلة حالياً.")

        st.markdown("#### الإنذارات الاستباقية للصحة الإلكترونية")
        alerts = (session.query(Alert)
                  .filter(Alert.department.in_(["الصحة الإلكترونية", "تقنية المعلومات"]))
                  .order_by(Alert.created_at.desc()).all())
        _alerts_table(alerts)

    elif "قسم الجودة" in selected_section:
        st.markdown("### مدير قسم الجودة - مؤشرات الأداء واتفاقيات مستوى الخدمة")
        st.info("متابعة التزام الأقسام التقنية بمعايير الجودة وزمن الاستجابة للبلاغات الطبية والتقنية.")
        
        kpis = session.query(KPI).all()
        if kpis:
            kpi_rows = [{"مؤشر الأداء": k.name, "القسم": k.department, "القيمة الحالية": f"{k.value} {k.unit}", 
                         "المستهدف": f"{k.target} {k.unit}", "الفترة": k.period, "التصنيف": k.category} for k in kpis]
            st.dataframe(pd.DataFrame(kpi_rows), width="stretch", hide_index=True)
        else:
            st.info("لا توجد مؤشرات أداء مسجلة حالياً.")

    elif "الأنظمة والتطبيقات" in selected_section:
        st.markdown("### قسم الأنظمة والتطبيقات - المهام الاستباقية")
        st.info("مراقبة استقرار التطبيقات والمنصات الداخلية وحالة خوادم التطبيقات وقواعد البيانات.")
        
        assets = session.query(SystemAsset).filter(SystemAsset.asset_type == "تطبيق").all()
        if assets:
            app_rows = [{"التطبيق": a.name, "القسم المالك": a.department, "الحالة": a.status,
                         "مستوى الأهمية": a.criticality, "المسؤول": a.owner} for a in assets]
            st.dataframe(pd.DataFrame(app_rows), width="stretch", hide_index=True)
        else:
            st.info("لا توجد تطبيقات مسجلة.")

    elif "البنية التحتية" in selected_section:
        st.markdown("### قسم البنية التحتية والشبكات - المهام الاستباقية")
        st.info("مراقبة أجهزة التوجيه، الخوادم الرئيسية، واتصال الأجهزة الحيوية مثل أجهزة العناية المركزة.")
        
        infra_assets = session.query(SystemAsset).filter(SystemAsset.asset_type.in_(["خادم", "جهاز شبكة"])).all()
        if infra_assets:
            infra_rows = [{"الأصل": a.name, "النوع": a.asset_type, "الحالة": a.status,
                           "عنوان IP": decrypt_field(a.ip_enc), "الأهمية": a.criticality} for a in infra_assets]
            st.dataframe(pd.DataFrame(infra_rows), width="stretch", hide_index=True)
        else:
            st.info("لا توجد أصول بنية تحتية مسجلة.")


# ---------------------------------------------------------------- الدعم الفني المتقدم
def _render_support_advanced(session, user):
    st.subheader("إدارة وتذاكر الدعم الفني وصيانة الأجهزة")
    
    status_filter = st.multiselect("تصفية حسب الحالة", ["مفتوحة", "قيد المعالجة", "مغلقة"],
                                    default=["مفتوحة", "قيد المعالجة"], key="support_status_flt")
    tickets = (session.query(Ticket).filter(Ticket.status.in_(status_filter))
               .order_by(Ticket.created_at.desc()).all()) if status_filter else []

    if not tickets:
        st.info("لا توجد بلاغات تطابق التصفية الحالية.")

    for t in tickets:
        with st.expander(f"[{t.ticket_number}] {t.title} — الحالة: {t.status}"):
            st.write(f"**الوصف:** {t.description or '-'}")
            st.write(f"**التصنيف العام:** {t.category} | **الموقع:** {t.location or '-'}")
            
            st.markdown("---")
            st.markdown("#### تشخيص فني الدعم")
            
            col_diag1, col_diag2 = st.columns(2)
            with col_diag1:
                fault_type = st.selectbox("نوع العطل المفحوص:", ["تقني (برمجيات/إعدادات)", "مادي / هاردوير (يحتاج صيانة)"], key=f"fault_type_{t.id}")
            with col_diag2:
                contractor = st.text_input("اسم الشركة المقاولة المسؤولة (إن وجد):", value="", key=f"contractor_{t.id}")

            send_to_contractor = st.text_input(
                "رسالة الإرسال الفوري للشركة المقاولة (اكتب الرسالة واضغط Enter للإرسال المباشر):",
                key=f"enter_msg_{t.id}",
                help="اكتب نص الملاحظة الموجهة للشركة المقاولة واضغط Enter لتسجيلها واعتمادها فوراً"
            )
            
            if send_to_contractor:
                st.toast(f"تم إرسال البلاغ بنجاح إلى الشركة المقاولة: {contractor or 'الشركة المعتمدة'} عبر النظام الآلي.")

            c1, c2, c3 = st.columns(3)
            with c1:
                new_status = st.selectbox("تحديث حالة البلاغ", ["مفتوحة", "قيد المعالجة", "مغلقة"],
                                           index=["مفتوحة", "قيد المعالجة", "مغلقة"].index(t.status),
                                           key=f"sup_status_{t.id}")
            with c2:
                assignee = st.text_input("مسند إلى الفني", value=t.assigned_to or "", key=f"sup_assign_{t.id}")
            with c3:
                notes = st.text_input("ملاحظات الحل النهائية", value=t.resolution_notes or "", key=f"sup_notes_{t.id}")
                
            if st.button("حفظ تحديث البلاغ", key=f"sup_save_{t.id}"):
                old_status = t.status
                t.status = new_status
                t.assigned_to = assignee or None
                t.resolution_notes = f"[{fault_type}] شركة الصيانة: {contractor or 'غير محدد'} - {notes or ''}"
                t.updated_at = datetime.utcnow()
                if new_status == "مغلقة" and old_status != "مغلقة":
                    t.resolved_at = datetime.utcnow()
                session.commit()
                log_action(session, user.username, user.role.value, "تحديث بلاغ دعم وصيانة",
                           f"{t.ticket_number}: نوع العطل: {fault_type} | المقاول: {contractor}", category="دعم فني")
                st.success("تم حفظ بيانات الصيانة والتحديث بنجاح.")
                st.rerun()

    st.divider()
    st.subheader("إنشاء بلاغ جديد (تقني أو مادي)")
    with st.form("it_advanced_new_ticket"):
        title = st.text_input("عنوان المشكلة / العطل")
        desc = st.text_area("وصف تفصيلي للعطل")
        category = st.selectbox("تصنيف العطل", ["الصحة الإلكترونية", "البنية التحتية", "الأنظمة والتطبيقات", "أجهزة مادية وهاردوير", "عام"])
        priority = st.selectbox("مستوى الأولوية", ["حرجة", "عالية", "متوسطة", "منخفضة"])
        location = st.text_input("الموقع (القسم / الغرفة / الطابق)")
        
        if st.form_submit_button("إنشاء البلاغ وإضافته للطابور"):
            if not title.strip():
                st.error("عنوان العطل مطلوب")
            else:
                count = session.query(Ticket).count() + 1
                ticket = Ticket(ticket_number=f"TCK-{count:04d}", title=title, description=desc,
                                 category=category, priority=priority, location=location,
                                 created_by=user.username, status="مفتوحة")
                session.add(ticket)
                session.commit()
                log_action(session, user.username, user.role.value, "إنشاء بلاغ جديد",
                           f"{ticket.ticket_number}: {title}", category="دعم فني")
                st.success(f"تم إنشاء البلاغ بنجاح برقم {ticket.ticket_number}")
                st.rerun()


# ---------------------------------------------------------------- Audit Log
def _render_audit(session):
    st.subheader("سجل التدقيق الأمني (غير قابل للتعديل)")
    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button("التحقق من سلامة السجل"):
            ok, bad_id = verify_chain(session)
            if ok:
                st.success("سلسلة السجل سليمة ولم يتم اكتشاف أي تلاعب.")
            else:
                st.error(f"تم اكتشاف عدم تطابق عند السجل رقم {bad_id}")
    with c2:
        st.caption("يعتمد السجل على سلسلة تجزئات مع قيود قاعدة بيانات تمنع الحذف أو التعديل.")

    severity_filter = st.multiselect("تصفية حسب الخطورة", ["info", "warning", "critical"],
                                      default=["info", "warning", "critical"], key="audit_sev_flt")
    logs = (session.query(AuditLog).filter(AuditLog.severity.in_(severity_filter))
            .order_by(AuditLog.timestamp.desc()).limit(300).all()) if severity_filter else []

    rows = [{"الوقت": l.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "المستخدم": l.username,
             "الدور": ROLE_LABELS.get(l.role, l.role), "الحدث": l.action, "الفئة": l.category,
             "الخطورة": l.severity, "التفاصيل": l.details} for l in logs]
    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch", hide_index=True, height=380)
    if not df.empty:
        st.download_button("تصدير CSV", df.to_csv(index=False).encode("utf-8-sig"),
                            file_name="audit_log_export.csv", mime="text/csv")


# ---------------------------------------------------------------- User Management
def _render_user_management(session, user):
    st.subheader("إدارة حسابات المستخدمين")
    users = session.query(User).all()
    rows = [{"اسم المستخدم": u.username, "الاسم": u.full_name, "الدور": ROLE_LABELS.get(u.role.value, u.role.value),
             "القسم": u.department, "نشط": "نعم" if u.is_active else "لا"} for u in users]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def _alerts_table(alerts):
    if not alerts:
        st.info("لا توجد إنذارات حالياً في هذا القسم.")
        return
    rows = [{"الخطورة": a.severity, "العنوان": a.title,
             "الوصف": a.description, "الحالة": a.status,
             "التاريخ": a.created_at.strftime("%Y-%m-%d %H:%M")} for a in alerts]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
