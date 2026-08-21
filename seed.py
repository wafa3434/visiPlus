"""
VisiPulse - سكربت التهيئة الأولية لقاعدة البيانات
- ينشئ الجداول ويفعّل قيود سجل التدقيق غير القابل للتعديل
- يزرع 3 حسابات أولية (تقنية معلومات / إدارة عليا / موظف) بكلمات مرور مؤقتة عشوائية
  يُطلب تغييرها إجبارياً عند أول تسجيل دخول
- يزرع بيانات تجريبية (تذاكر، إنذارات، أصول، مؤشرات أداء، قرارات) لتجربة النظام مباشرة

التشغيل: python seed.py
"""
import secrets
import string

from database import init_db, get_session
from models import User, UserRole, Ticket, Alert, SystemAsset, KPI, Decision
from security import hash_password, encrypt_field
from audit import log_action


def _random_temp_password(length: int = 14) -> str:
    """يولّد كلمة مرور مؤقتة عشوائية مطابقة للسياسة (يُجبر المستخدم على تغييرها لاحقاً)."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in pwd) and any(c.isupper() for c in pwd)
                and any(c.isdigit() for c in pwd) and any(c in "!@#$%^&*" for c in pwd)):
            return pwd


def _create_user(session, username, full_name, role, department, email, phone):
    if session.query(User).filter(User.username == username).first():
        return None
    temp_pwd = _random_temp_password()
    user = User(
        username=username,
        full_name=full_name,
        role=role,
        department=department,
        password_hash=hash_password(temp_pwd),
        must_change_password=True,
        email_enc=encrypt_field(email),
        phone_enc=encrypt_field(phone),
    )
    session.add(user)
    session.commit()
    print(f"[+] تم إنشاء المستخدم: {username:<20} | الدور: {role.value:<10} | كلمة المرور المؤقتة: {temp_pwd}")
    return user


def seed():
    init_db()
    session = get_session()

    if session.query(User).count() == 0:
        print("=" * 78)
        print("إنشاء الحسابات الأولية - احتفظ بكلمات المرور المؤقتة أدناه في مكان آمن")
        print("سيُطلب من كل مستخدم تغيير كلمة المرور إجبارياً عند أول تسجيل دخول")
        print("=" * 78)
        _create_user(session, "it_admin", "مدير تقنية المعلومات", UserRole.IT,
                     "تقنية المعلومات", "it_admin@hospital.local", "0500000001")
        _create_user(session, "hospital_director", "مدير المستشفى", UserRole.EXECUTIVE,
                     "الإدارة العليا", "director@hospital.local", "0500000002")
        _create_user(session, "employee1", "موظف تجريبي", UserRole.EMPLOYEE,
                     "قسم الطوارئ", "employee1@hospital.local", "0500000003")
        log_action(session, "system", "system", "تهيئة النظام", "تم إنشاء الحسابات الأولية", category="نظام")
        print("=" * 78)
    else:
        print("يوجد مستخدمون بالفعل في قاعدة البيانات — تم تخطي إنشاء الحسابات الأولية")

    if session.query(Ticket).count() == 0:
        session.add_all([
            Ticket(ticket_number="TCK-0001", title="عطل في جهاز عرض الأشعة",
                   description="لا يعمل جهاز عرض صور الأشعة في قسم الطوارئ منذ الصباح",
                   category="البنية التحتية", priority="حرجة", status="مفتوحة",
                   location="قسم الطوارئ - الطابق الأول", created_by="employee1"),
            Ticket(ticket_number="TCK-0002", title="بطء في نظام الملفات الإلكترونية",
                   description="بطء ملحوظ عند فتح ملفات المرضى في نظام HIS",
                   category="الصحة الإلكترونية", priority="عالية", status="قيد المعالجة",
                   location="العيادات الخارجية", created_by="employee1", assigned_to="it_admin"),
        ])

    if session.query(Alert).count() == 0:
        session.add_all([
            Alert(title="ارتفاع استخدام المعالج على خادم HIS الرئيسي",
                  description="استخدام المعالج تجاوز 90% لمدة 10 دقائق متتالية",
                  source_system="خادم نظام معلومات المستشفى (HIS)", department="تقنية المعلومات",
                  severity="عالية", status="نشط", created_by="النظام"),
            Alert(title="انقطاع اتصال جهاز مراقبة في العناية المركزة",
                  description="فقدان الاتصال بجهاز المراقبة رقم ICU-07 عن الشبكة الطبية",
                  source_system="شبكة الأجهزة الطبية", department="العناية المركزة",
                  severity="حرجة", status="نشط", created_by="النظام"),
        ])

    if session.query(SystemAsset).count() == 0:
        session.add_all([
            SystemAsset(name="خادم نظام معلومات المستشفى HIS-01", asset_type="خادم",
                        department="الصحة الإلكترونية", ip_enc=encrypt_field("10.10.1.10"),
                        status="يعمل", criticality="حرجة", owner="it_admin"),
            SystemAsset(name="جهاز توجيه الشبكة الرئيسي - المبنى A", asset_type="جهاز شبكة",
                        department="البنية التحتية", ip_enc=encrypt_field("10.10.0.1"),
                        status="يعمل", criticality="حرجة", owner="it_admin"),
            SystemAsset(name="تطبيق حجز المواعيد الإلكتروني", asset_type="تطبيق",
                        department="الأنظمة والتطبيقات", ip_enc=encrypt_field("10.10.2.20"),
                        status="يعمل", criticality="متوسطة", owner="it_admin"),
        ])

    if session.query(KPI).count() == 0:
        session.add_all([
            KPI(name="نسبة توفر الأنظمة الحرجة", department="تقنية المعلومات",
                value="99.4", target="99.9", unit="%", period="الشهر الحالي", category="SLA"),
            KPI(name="متوسط زمن الاستجابة لبلاغات الدعم الفني", department="تقنية المعلومات",
                value="42", target="30", unit="دقيقة", period="الشهر الحالي", category="SLA"),
            KPI(name="نسبة إغلاق البلاغات ضمن الوقت المتفق عليه", department="تقنية المعلومات",
                value="87", target="95", unit="%", period="الشهر الحالي", category="جودة"),
        ])

    if session.query(Decision).count() == 0:
        session.add_all([
            Decision(title="اعتماد ترقية الجدار الناري المركزي",
                     description="ترقية ضرورية لمواكبة متطلبات الهيئة الوطنية للأمن السيبراني (NCA)",
                     category="أمن سيبراني", status="بانتظار الاعتماد", submitted_by="it_admin"),
            Decision(title="اعتماد خطة التعافي من الكوارث السنوية",
                     description="مراجعة واعتماد خطة استمرارية الأعمال والتعافي من الكوارث للعام القادم",
                     category="استمرارية الأعمال", status="بانتظار الاعتماد", submitted_by="it_admin"),
        ])

    session.commit()
    session.close()
    print("تم تجهيز قاعدة البيانات والبيانات التجريبية بنجاح ✅")


if __name__ == "__main__":
    seed()
