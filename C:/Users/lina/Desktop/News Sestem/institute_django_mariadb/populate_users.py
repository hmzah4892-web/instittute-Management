# populate_users.py
"""Utility script to create initial user accounts and reference data.
Run with:
    venv\Scripts\python populate_users.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'institute_django.settings')
django.setup()

from institute.models import User, SLevel, Section, Specialty, Administration, EmployeeProfile, TeacherProfile, StudentProfile, Subject
from django.contrib.auth import get_user_model

def create_user(username, password, role, **extra):
    User = get_user_model()
    if not User.objects.filter(username=username).exists():
        user = User.objects.create_user(username=username, password=password, role=role, **extra)
        print(f"Created user: {username} ({role})")
        return user
    else:
        user = User.objects.get(username=username)
        user.set_password(password)
        user.role = role
        for k, v in extra.items():
            setattr(user, k, v)
        user.save()
        print(f"Updated user: {username} ({role})")
        return user

def main():
    # 1. Create SLevel (المستويات)
    level1, _ = SLevel.objects.get_or_create(lev_no=1, defaults={'lev_name': 'المستوى الأول'})
    level2, _ = SLevel.objects.get_or_create(lev_no=2, defaults={'lev_name': 'المستوى الثاني'})
    level3, _ = SLevel.objects.get_or_create(lev_no=3, defaults={'lev_name': 'المستوى الثالث'})

    # 2. Create Section (الأقسام)
    sec_admin, _ = Section.objects.get_or_create(sec_no=1, defaults={'sec_name': 'الأقسام الإدارية'})
    sec_medical, _ = Section.objects.get_or_create(sec_no=2, defaults={'sec_name': 'الأقسام الطبية'})

    # 3. Create Specialty (التخصصات)
    # الأقسام الإدارية: محاسبة، جرافيكس، برمجيات (مستوى أول ومستوى ثاني)
    specs_data = [
        # محاسبة
        (1, 'محاسبة - مستوى أول', level1, sec_admin),
        (2, 'محاسبة - مستوى ثاني', level2, sec_admin),
        # جرافيكس
        (3, 'جرافيكس - مستوى أول', level1, sec_admin),
        (4, 'جرافيكس - مستوى ثاني', level2, sec_admin),
        # برمجيات
        (5, 'برمجيات - مستوى أول', level1, sec_admin),
        (6, 'برمجيات - مستوى ثاني', level2, sec_admin),
        
        # الأقسام الطبية: مساعد طبيب، قبالة، مختبرات (ثلاثة مستويات)
        # مساعد طبيب
        (7, 'مساعد طبيب - مستوى أول', level1, sec_medical),
        (8, 'مساعد طبيب - مستوى ثاني', level2, sec_medical),
        (9, 'مساعد طبيب - مستوى ثالث', level3, sec_medical),
        # قبالة
        (10, 'قبالة - مستوى أول', level1, sec_medical),
        (11, 'قبالة - مستوى ثاني', level2, sec_medical),
        (12, 'قبالة - مستوى ثالث', level3, sec_medical),
        # مختبرات
        (13, 'مختبرات - مستوى أول', level1, sec_medical),
        (14, 'مختبرات - مستوى ثاني', level2, sec_medical),
        (15, 'مختبرات - مستوى ثالث', level3, sec_medical),
    ]

    for spec_no, spec_name, lvl, sec in specs_data:
        Specialty.objects.update_or_create(
            spec_no=spec_no,
            defaults={'spec_name': spec_name, 'level': lvl, 'section': sec}
        )

    # Administration entry
    admin_dep, _ = Administration.objects.get_or_create(admin_no=1, defaults={'admin_name': 'إدارة المعهد', 'admin_type': 'رئيسي'})

    # Delete old usernames that we will replace to prevent leftover conflicts
    User = get_user_model()
    old_usernames = ['faculty', 'student', 'admission', 'finance', 'staff', 'dr_ahmed', 'std_ali', 'staff_nour']
    User.objects.filter(username__in=old_usernames).delete()

    # Create users for each role
    manager = create_user('manager', '123456', 'manager', first_name='د. عبدالعزيز', last_name='المخلافي')
    admin = create_user('admin', '123456', 'admin', first_name='م. عمر', last_name='الدعيس')
    faculty = create_user('shihab', '123456', 'faculty', first_name='أ. شهاب', last_name='مدرس الإنجليزي')
    student = create_user('abdullah', '123456', 'student', first_name='عبدالله', last_name='الرعيني')
    admission = create_user('adm_sara', '123456', 'admission', first_name='سارة', last_name='العتيبي')
    finance = create_user('fin_omar', '123456', 'finance', first_name='عمر', last_name='الحربي')
    staff = create_user('manal', '123456', 'staff', first_name='أ. منال', last_name='الإدارة')
    hr_user = create_user('hr_ali', '123456', 'hr', first_name='أ. علي', last_name='الموارد البشرية')

    # Link profiles
    EmployeeProfile.objects.get_or_create(user=manager, defaults={'job_title': 'مدير عام المعهد', 'administration': admin_dep, 'hire_date': '2020-01-01'})
    EmployeeProfile.objects.get_or_create(user=admin, defaults={'job_title': 'مشرف النظام', 'administration': admin_dep, 'hire_date': '2020-01-01'})
    
    teacher_prof, _ = TeacherProfile.objects.get_or_create(user=faculty, defaults={'specialty': Specialty.objects.get(spec_no=5), 'contract_date': '2021-01-01'})
    
    StudentProfile.objects.get_or_create(
        user=student, 
        defaults={
            'specialty': Specialty.objects.get(spec_no=5), # برمجيات - مستوى أول
            'level': level1, 
            'section': sec_admin, 
            'birth_date': '2005-05-05'
        }
    )
    
    # Additional staff profiles
    EmployeeProfile.objects.get_or_create(user=admission, defaults={'job_title': 'مسؤول قبول وتسجيل', 'administration': admin_dep, 'hire_date': '2020-01-01'})
    EmployeeProfile.objects.get_or_create(user=finance, defaults={'job_title': 'مسؤول الشؤون المالية', 'administration': admin_dep, 'hire_date': '2020-01-01'})
    EmployeeProfile.objects.get_or_create(user=staff, defaults={'job_title': 'إدارية', 'administration': admin_dep, 'hire_date': '2020-01-01'})
    EmployeeProfile.objects.get_or_create(user=hr_user, defaults={'job_title': 'مسؤول الموارد البشرية', 'administration': admin_dep, 'hire_date': '2020-01-01'})

    # 4. Create Subject (مقرر انجليزي للمدرس شهاب)
    Subject.objects.update_or_create(
        sub_no=101,
        defaults={
            'sub_name': 'اللغة الإنجليزية',
            'hours': 3,
            'level': level1,
            'specialty': Specialty.objects.get(spec_no=5),
            'teacher': teacher_prof
        }
    )

    print("Initial data population complete.")

if __name__ == '__main__':
    main()
