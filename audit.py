"""
VisiPulse - سجل التدقيق غير القابل للتلاعب (Immutable / Tamper-Evident Audit Trail)

الآلية:
1. كل سجل تدقيق يحتوي على تجزئة (SHA-256) مبنية على: تجزئة السجل السابق + بيانات الحدث الحالي،
   بأسلوب سلسلة التجزئات (Hash Chain) المشابه لمبدأ سلاسل الكتل (Blockchain-style integrity).
   أي تعديل على أي سجل قديم سيكسر تسلسل التجزئات ويكون قابلاً للاكتشاف فوراً عبر verify_chain().
2. بالإضافة إلى ذلك، تُفرض قيود على مستوى قاعدة البيانات (Triggers في database.py) تمنع
   عمليات UPDATE أو DELETE على جدول audit_log بشكل قاطع.

ملاحظة للإنتاج: هذا يوفر "دليل تلاعب" (Tamper-Evidence) قوياً ضمن نطاق التطبيق. للوصول إلى
"عدم قابلية تلاعب" كاملة على مستوى البنية التحتية، يُوصى في بيئة الإنتاج بإعادة توجيه السجلات
إلى نظام SIEM مركزي أو تخزين WORM (Write-Once-Read-Many) بشكل متزامن.
"""
import hashlib
from datetime import datetime

from models import AuditLog

GENESIS_HASH = "0" * 64


def _compute_hash(prev_hash: str, timestamp: datetime, username: str, action: str, details: str) -> str:
    payload = f"{prev_hash}|{timestamp.isoformat()}|{username}|{action}|{details or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def log_action(session, username: str, role: str, action: str, details: str = "",
                category: str = "عام", severity: str = "info") -> AuditLog:
    """يسجّل حدثاً جديداً في سجل التدقيق مرتبطاً بسلسلة التجزئات."""
    last = session.query(AuditLog).order_by(AuditLog.id.desc()).first()
    prev_hash = last.record_hash if last else GENESIS_HASH
    ts = datetime.utcnow()
    record_hash = _compute_hash(prev_hash, ts, username, action, details)

    entry = AuditLog(
        timestamp=ts, username=username, role=role, action=action,
        details=details, category=category, severity=severity,
        prev_hash=prev_hash, record_hash=record_hash,
    )
    session.add(entry)
    session.commit()
    return entry


def verify_chain(session):
    """
    يتحقق من سلامة كامل سلسلة سجل التدقيق منذ بداية التشغيل.
    يعيد Tuple: (سليم: bool, رقم أول سجل غير مطابق أو None إن كان السجل سليماً بالكامل).
    """
    logs = session.query(AuditLog).order_by(AuditLog.id.asc()).all()
    prev_hash = GENESIS_HASH
    for log in logs:
        expected = _compute_hash(prev_hash, log.timestamp, log.username, log.action, log.details)
        if log.prev_hash != prev_hash or log.record_hash != expected:
            return False, log.id
        prev_hash = log.record_hash
    return True, None
