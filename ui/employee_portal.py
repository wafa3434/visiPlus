"""
VisiPulse - بوابة الموظف العادي (Standard Employee Portal)
تضم: شاشة الإنذار الاستباقي ورصد الأعطال الميدانية | إرسال البلاغات وتتبع حالتها
"""
import streamlit as st
import pandas as pd

from models import Ticket, Alert
from audit import log_action

SEVERITY_ICONS = {"حرجة": "🔴", "عالية": "🟠", "متوسطة": "🟡", "منخفضة": "🟢"}


def render(session, user):
    st.title("👤 بوابة الموظف")
    st.caption(f"مرحباً {user.full_name} | القسم: {user.department or '-'}")

    tab1, tab2 = st.tabs(["🚨 الإنذار الاستباقي ورصد الأعطال", "📨 بلاغاتي"])

    with tab1:
        _render_alerts_feed(session)
    with tab2:
        _render_my_tickets(session, user)


def _render_alerts_feed(session):
    st.subheader("الإنذارات النشطة")
    alerts = session.query(Alert).filter(Alert.status == "نشط").order_by(Alert.created_at.desc()).all()
    if not alerts:
        st.success("لا توجد إنذارات نشطة حالياً ✅")

    for a in alerts:
        with st.container(border=True):
            st.markdown(f"### {SEVERITY_ICONS.get(a.severity, '')} {a.title}")
            st.write(a.description or "-")
            st.caption(f"القسم: {a.department} | المصدر: {a.source_system} | {a.created_at:%Y-%m-%d %H:%M}")

    st.divider()
    st.info("رصدت عطلاً ميدانياً لم يظهر ضمن الإنذارات أعلاه؟ استخدم تبويب «بلاغاتي» لإرسال بلاغ فوري لفريق الدعم الفني.")


def _render_my_tickets(session, user):
    st.subheader("إرسال بلاغ جديد")
    with st.form("employee_new_ticket"):
        title = st.text_input("عنوان البلاغ")
        desc = st.text_area("وصف العطل / المشكلة")
        category = st.selectbox("التصنيف", ["الصحة الإلكترونية", "البنية التحتية", "الأنظمة والتطبيقات", "عام"])
        priority = st.selectbox("مدى الإلحاح", ["حرجة", "عالية", "متوسطة", "منخفضة"], index=2)
        location = st.text_input("الموقع (القسم / الغرفة)")
        if st.form_submit_button("إرسال البلاغ"):
            if not title.strip():
                st.error("عنوان البلاغ مطلوب")
            else:
                count = session.query(Ticket).count() + 1
                ticket = Ticket(ticket_number=f"TCK-{count:04d}", title=title, description=desc,
                                 category=category, priority=priority, location=location,
                                 created_by=user.username, status="مفتوحة")
                session.add(ticket)
                session.commit()
                log_action(session, user.username, user.role.value, "إرسال بلاغ",
                           f"{ticket.ticket_number}: {title}", category="دعم فني")
                st.success(f"تم إرسال البلاغ برقم {ticket.ticket_number} وسيتم التعامل معه من قبل الدعم الفني")
                st.rerun()

    st.divider()
    st.subheader("متابعة بلاغاتي السابقة")
    my_tickets = (session.query(Ticket).filter(Ticket.created_by == user.username)
                  .order_by(Ticket.created_at.desc()).all())
    if not my_tickets:
        st.info("لم تقم بإرسال أي بلاغات بعد.")
        return

    rows = [{"رقم البلاغ": t.ticket_number, "العنوان": t.title, "الحالة": t.status,
             "الأولوية": t.priority, "تاريخ الإرسال": t.created_at.strftime("%Y-%m-%d %H:%M"),
             "آخر تحديث": t.updated_at.strftime("%Y-%m-%d %H:%M")} for t in my_tickets]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
