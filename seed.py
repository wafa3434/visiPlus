"""
VisiPulse - سكربت التهيئة الأولية لقاعدة البيانات
- ينشئ الجداول ويفعّل قيود سجل التدقيق غير القابل للتعديل
- يزرع 3 حسابات أولية مستقلة (لكل حساب اسم مستخدم، بريد، وكلمة مرور خاصة)
- يزرع بيانات تجريبية لتجربة النظام مباشرة

التشغيل: python seed.py
"""
from database import init_db, get_session
from models import User, UserRole, Ticket, Alert, SystemAsset, KPI, Decision
from security import hash_password, encrypt_field
from audit import log_action


def _create_or_update_user(session, username, full_name, role, department, email, phone, raw_password):
    existing_user = session.query(User).filter(User.username == username).first()
    
    if existing_user:
        existing_user.full_name = full_name
        existing_user.role = role
        existing_user.department = department
        existing_user.password_hash = hash_password(raw_password)
        existing_user.must_change_password = False
        existing_user.email_enc = encrypt_field(email)
        existing_user.phone_enc = encrypt_field(phone)
        session.commit()
        print(f"تم تحديث المستخدم: {username} | كلمة المرور: {raw_password}")
        return existing_user

    user = User(
        username=username,
        full_name=full_name,
        role=role,
        department=department,
        password_hash=hash_password(raw_password),
        must_change_password=False,
        email_enc=encrypt_field(email),
        phone_enc=encrypt_field(phone),
    )
    session.add(user)
    session.commit()
    print(f"تم إنشاء المستخدم: {username} | كلمة المرور: {raw_password}")
    return user


def seed():
    init_db()
    session = get_session()

    print("=" * 78)
    print("إعداد وتحديث الحسابات الأولية المستقلة للنظام")
    print("=" * 78)
    
    # 1. حساب تقنية المعلومات
    _create_or_update_user(
        session, 
        username="it_admin", 
        full_name="مدير تقنية المعلومات", 
        role=UserRole.IT,
        department="تقنية المعلومات", 
        email="it_admin@hospital.local", 
        phone="0500000001",
        raw_password="ItAdmin@2026_Secure!"
    )
    
    # 2. حساب الإدارة العليا
    _create_or_update_user(
        session, 
        username="hospital_director", 
        full_name="مدير المستشفى", 
        role=UserRole.EXECUTIVE,
        department="الإدارة العليا", 
        email="director@hospital.local", 
        phone="0500000002",
        raw_password="Director@2026_Secure!"
    )
    
    # 3. حساب الموظف
    _create_or_update_user(
        session, 
        username="employee1", 
        full_name="موظف تجريبي", 
        role=UserRole.EMPLOYEE,
        department="قسم الطوارئ", 
        email="employee1@hospital.local", 
        phone="0500000003",
        raw_password="Employee@2026_Secure!"
    )
    
    log_action(session, "system", "system", "تهيئة النظام", "تم ضبط الحسابات الأولية المستقلة", category="نظام")
    print("=" * 78)

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
                     description="ترقية ضرورية لمواكبة متطلبات الهيئة الوطنية للأمن السيبراني",
                     category="أمن سيبراني", status="بانتظار الاعتماد", submitted_by="it_admin"),
            Decision(title="اعتماد خطة التعافي من الكوارث السنوية",
                     description="مراجعة واعتماد خطة استمرارية الأعمال والتعافي من الكوارث للعام القادم",
                     category="استمرارية الأعمال", status="بانتظار الاعتماد", submitted_by="it_admin"),
        ])

    session.commit()
    session.close()
    print("تم تحديث وتجهيز قاعدة البيانات بالحسابات المستقلة بنجاح")


if __name__ == "__main__":
    seed()
