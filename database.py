"""
VisiPulse - إعداد قاعدة البيانات (SQLAlchemy Engine / Session)
يقوم أيضاً بتفعيل قيود على مستوى قاعدة البيانات تمنع تعديل أو حذف سجل التدقيق نهائياً،
بما يعزز خاصية "سجل التدقيق غير القابل للتلاعب" على مستوى الـ Database Engine
وليس فقط على مستوى منطق التطبيق.
"""
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from models import Base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///visipulse.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


# قيود قاعدة البيانات (Triggers) لمنع تعديل/حذف سجل التدقيق - دفاع متعدد الطبقات
# إلى جانب سلسلة التجزئات (Hash Chain) في audit.py
_AUDIT_IMMUTABILITY_TRIGGERS = [
    """
    CREATE TRIGGER IF NOT EXISTS trg_audit_no_update
    BEFORE UPDATE ON audit_log
    BEGIN
        SELECT RAISE(ABORT, 'VisiPulse: سجل التدقيق للقراءة فقط - التعديل غير مسموح');
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_audit_no_delete
    BEFORE DELETE ON audit_log
    BEGIN
        SELECT RAISE(ABORT, 'VisiPulse: سجل التدقيق للقراءة فقط - الحذف غير مسموح');
    END;
    """,
]


def init_db():
    """ينشئ كافة الجداول (إن لم تكن موجودة) ويفعّل قيود عدم قابلية التعديل/الحذف لسجل التدقيق."""
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        for trigger_sql in _AUDIT_IMMUTABILITY_TRIGGERS:
            conn.execute(text(trigger_sql))


def get_session():
    """يعيد جلسة SQLAlchemy جديدة."""
    return SessionLocal()
