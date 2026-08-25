"""
VisiPulse - بوابة الإدارة العليا (Executive / Hospital Director Portal)
تضم: مؤشرات الأداء الرئيسية ومستوى الخدمة (KPI/SLA) | مراجعة واعتماد القرارات الاستراتيجية وتقارير الامتثال
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timezone

from models import KPI, Decision, Ticket, Alert, AuditLog
from audit import log_action, verify_chain

SEVERITY_ICONS = {"حرجة": "🔴", "عالية": "🟠", "متوسطة": "🟡", "منخفضة": "🟢"}


def render(session, user):
    st.title("🏛️ بوابة الإدارة العليا")
    st.caption(f"مرحباً {user.full_name}")

    tab1, tab2 = st.tabs(["📊 مؤشرات الأداء ومستوى الخدمة", "✅ القرارات الاستراتيجية والامتثال"])

    with tab1:
        _render_kpis(session)
    with tab2:
        _render_decisions(session, user)


def _render_kpis(session):
    st.subheader("لوحة مؤشرات الأداء الرئيسية (KPI) ومستوى الخدمة (SLA)")
    kpis = session.query(KPI).all()
    if kpis:
        cols = st.columns(3)
        for i, k in enumerate(kpis):
            with cols[i % 3]:
                diff = None
                try:
                    diff = float(k.value) - float(k.target)
                except (TypeError, ValueError):
                    pass
                st.metric(k.name, f"{k.value} {k.unit}",
                          delta=f"{diff:+.1f} عن الهدف" if diff is not None else None,
                          delta_color="normal" if (diff is not None and diff >= 0) else "inverse")
                st.caption(f"الهدف: {k.target} {k.unit} | {k.period}")
    else:
        st.info("لا توجد مؤشرات أداء مسجلة بعد.")

    st.divider()
    st.subheader("نظرة عامة تشغيلية")
    c1, c2, c3, c4 = st.columns(4)
    open_tickets = session.query(Ticket).filter(Ticket.status != "مغلقة").count()
    critical_alerts = session.query(Alert).filter(Alert.status == "نشط", Alert.severity == "حرجة").count()
    total_tickets = session.query(Ticket).count()
    closed = session.query(Ticket).filter(Ticket.status == "مغلقة").count()
    resolution_rate = f"{(closed / total_tickets * 100):.0f}%" if total_tickets else "—"

    c1.metric("بلاغات مفتوحة", open_tickets)
    c2.metric("إنذارات حرجة نشطة", critical_alerts)
    c3.metric("إجمالي البلاغات", total_tickets)
    c4.metric("نسبة إغلاق البلاغات", resolution_rate)

    tickets = session.query(Ticket).order_by(Ticket.created_at).all()
    if tickets:
        df = pd.DataFrame([{"التاريخ": t.created_at.date(), "التصنيف": t.category} for t in tickets if t.created_at])
        if not df.empty:
            trend = df.groupby(["التاريخ", "التصنيف"]).size().unstack(fill_value=0)
            st.markdown("**اتجاه البلاغات حسب التصنيف**")
            st.bar_chart(trend)


def _render_decisions(session, user):
    st.subheader("القرارات الاستراتيجية بانتظار الاعتماد")
    pending = session.query(Decision).filter(Decision.status == "بانتظار الاعتماد").all()
    if not pending:
        st.success("لا توجد قرارات بانتظار الاعتماد حالياً ✅")

    for d in pending:
        with st.container(border=True):
            st.markdown(f"#### {d.title}")
            st.write(d.description)
            formatted_date = d.created_at.strftime("%Y-%m-%d") if d.created_at else "-"
            st.caption(f"التصنيف: {d.category} | مقدَّم من: {d.submitted_by} | {formatted_date}")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ اعتماد", key=f"approve_{d.id}"):
                    d.status = "معتمد"
                    d.approved_by = user.username
                    d.decided_at = datetime.now(timezone.utc)
                    session.commit()
                    log_action(session, user.username, user.role.value, "اعتماد قرار", d.title,
                               category="حوكمة", severity="warning")
                    st.success("تم الاعتماد")
                    st.rerun()
            with c2:
                if st.button("❌ رفض", key=f"reject_{d.id}"):
                    d.status = "مرفوض"
                    d.approved_by = user.username
                    d.decided_at = datetime.now(timezone.utc)
                    session.commit()
                    log_action(session, user.username, user.role.value, "رفض قرار", d.title,
                               category="حوكمة", severity="warning")
                    st.warning("تم الرفض")
                    st.rerun()

    st.divider()
    st.subheader("تقرير الامتثال والتحسين المستمر")
    ok, bad_id = verify_chain(session)
    audit_status = "سليم ✅" if ok else f"⚠️ تلاعب مكتشف عند السجل رقم {bad_id}"
    total_events = session.query(AuditLog).count()

    c1, c2 = st.columns(2)
    c1.metric("حالة سلامة سجل التدقيق", audit_status)
    c2.metric("إجمالي الأحداث المسجلة", total_events)

    history = (session.query(Decision).filter(Decision.status != "بانتظار الاعتماد")
               .order_by(Decision.decided_at.desc()).all())
    if history:
        rows = [{
            "القرار": d.title, 
            "الحالة": d.status, 
            "اعتمده": d.approved_by,
            "التاريخ": d.decided_at.strftime("%Y-%m-%d") if d.decided_at else "-"
        } for d in history]
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("⬇️ تصدير تقرير القرارات CSV", df.to_csv(index=False).encode("utf-8-sig"),
                            file_name="compliance_decisions_report.csv", mime="text/csv")
    else:
        st.caption("لا توجد قرارات مُعتمدة أو مرفوضة بعد لعرضها في السجل التاريخي.")
