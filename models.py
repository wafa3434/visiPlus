"""
VisiPulse - نماذج قاعدة البيانات (SQLAlchemy ORM Models)
نظام الإنذار المبكر وحوكمة البنية التحتية للمنشآت الصحية
"""
import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SAEnum
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class UserRole(str, enum.Enum):
    """أدوار النظام الثلاثة - كل دور يُوجَّه إلى بوابة منفصلة تماماً بعد تسجيل الدخول."""
    IT = "it"
    EXECUTIVE = "executive"
    EMPLOYEE = "employee"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(150), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False)
    department = Column(String(100))

    password_hash = Column(String(255), nullable=False)
    password_changed_at = Column(DateTime, default=datetime.utcnow)
    must_change_password = Column(Boolean, default=True)

    failed_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    # حقول حساسة مشفّرة (Fernet) - انظر security.py
    email_enc = Column(Text)
    phone_enc = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)


class PasswordHistory(Base):
    """سجل كلمات المرور السابقة لمنع إعادة استخدامها (Password Reuse Prevention)."""
    __tablename__ = "password_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    """
    سجل تدقيق غير قابل للتلاعب (Immutable Audit Trail):
    - محمي منطقياً بسلسلة تجزئات SHA-256 (Hash Chain) تكشف أي تعديل لاحق.
    - محمي على مستوى قاعدة البيانات بقيود (Triggers) تمنع UPDATE / DELETE (انظر database.py).
    """
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    username = Column(String(50))
    role = Column(String(50))
    action = Column(String(150))
    category = Column(String(50))
    severity = Column(String(20), default="info")  # info / warning / critical
    details = Column(Text)
    prev_hash = Column(String(128))
    record_hash = Column(String(128))


class Ticket(Base):
    """بلاغات الدعم الفني (تُنشأ من بوابة الموظف أو داخلياً من بوابة IT)."""
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    ticket_number = Column(String(30), unique=True)
    title = Column(String(200))
    description = Column(Text)
    category = Column(String(100))   # الصحة الإلكترونية / البنية التحتية / الأنظمة والتطبيقات / عام
    priority = Column(String(20))    # حرجة / عالية / متوسطة / منخفضة
    status = Column(String(30), default="مفتوحة")  # مفتوحة / قيد المعالجة / مغلقة
    location = Column(String(150))
    created_by = Column(String(50))
    assigned_to = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)


class Alert(Base):
    """الإنذارات الاستباقية (تُعرض في بوابة الموظف وبوابة IT)."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    title = Column(String(200))
    description = Column(Text)
    source_system = Column(String(100))
    department = Column(String(100))
    severity = Column(String(20))     # حرجة / عالية / متوسطة / منخفضة
    status = Column(String(30), default="نشط")  # نشط / تم الحل
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    created_by = Column(String(50))


class SystemAsset(Base):
    """جرد أصول تقنية المعلومات: خوادم، أجهزة شبكة، تطبيقات (تشمل قسمي البنية التحتية والأنظمة)."""
    __tablename__ = "system_assets"

    id = Column(Integer, primary_key=True)
    name = Column(String(150))
    asset_type = Column(String(50))    # خادم / جهاز شبكة / تطبيق
    department = Column(String(100))
    ip_enc = Column(Text)              # عنوان IP مشفّر (Fernet)
    status = Column(String(30), default="يعمل")
    criticality = Column(String(20))   # حرجة / عالية / متوسطة / منخفضة
    last_maintenance = Column(DateTime, nullable=True)
    owner = Column(String(100))


class KPI(Base):
    """مؤشرات الأداء الرئيسية ومستويات جودة الخدمة (KPI / SLA) - بوابة الإدارة العليا."""
    __tablename__ = "kpis"

    id = Column(Integer, primary_key=True)
    name = Column(String(150))
    department = Column(String(100))
    value = Column(String(50))
    target = Column(String(50))
    unit = Column(String(30))
    period = Column(String(30))
    category = Column(String(50))   # SLA / جودة / أداء
    updated_at = Column(DateTime, default=datetime.utcnow)


class Decision(Base):
    """القرارات الاستراتيجية وتقارير الامتثال - تعتمدها الإدارة العليا."""
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True)
    title = Column(String(200))
    description = Column(Text)
    category = Column(String(100))
    status = Column(String(30), default="بانتظار الاعتماد")  # بانتظار الاعتماد / معتمد / مرفوض
    submitted_by = Column(String(50))
    approved_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
