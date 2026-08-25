"""
VisiPulse - إعداد قاعدة البيانات (SQLAlchemy Engine / Session)
يقوم أيضاً بتفعيل قيود على مستوى قاعدة البيانات تمنع تعديل أو حذف سجل التدقيق نهائياً،
بما يعزز خاصية "سجل التدقيق غير القابل للتلاعب" على مستوى الـ Database Engine
وليس فقط على مستوى منطق التطبيق.
"""
import os
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from models import Base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///visipulse.db")

# ضبط الخصائص بناءً على نوع قاعدة البيانات
engine_args = {}
if "sqlite" in DATABASE_URL:
    engine_args["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


# قيود قاعدة البيانات (Triggers) لمنع تعديل/حذف سجل التدقيق (خاصة بـ SQLite)
_SQLITE_AUDIT_IMMUTABILITY_TRIGGERS = [
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
    
    # تطبيق التريغرز فقط إذا كانت قاعدة البيانات SQLite
    if "sqlite" in DATABASE_URL:
        with engine.begin() as conn:
            for trigger_sql in _SQLITE_AUDIT_IMMUTABILITY_TRIGGERS:
                conn.execute(text(trigger_sql))


def get_session():
    """يعيد جلسة SQLAlchemy جديدة (للاستخدام اليدوي)."""
    return SessionLocal()


@contextmanager
def get_db():
    """
    مدير سياق (Context Manager) لإدارة جلسات قاعدة البيانات بأمان
    وضمان إغلاق الجلسة تلقائياً بعد الانتهاء منها.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
