"""
خدمات الشؤون الأكاديمية — Academic Service Layer
==================================================
تتولى العمليات الأكاديمية:
- إدارة السنوات الدراسية (Academic Years)
- الأقسام والتخصصات والمناهج
- تسجيل وإسقاط المقررات
"""
from django.utils import timezone
from institute.models import (
    Result, Subject, Section, SLevel, Specialty,
    Semester, AcademicYear, EmployeeProfile, TeacherProfile,
    RoleChoices, ContractType
)


def get_current_academic_year():
    """الحصول على السنة الأكاديمية الحالية"""
    year = AcademicYear.objects.filter(is_current=True).first()
    if not year:
        # إنشاء سنة افتراضية إذا لم توجد
        from datetime import date
        year = AcademicYear.objects.create(
            name=f"{date.today().year}-{date.today().year + 1}",
            start_date=date(date.today().year, 9, 1),
            end_date=date(date.today().year + 1, 6, 30),
            is_current=True
        )
    return year


def get_active_semester(level):
    """الحصول على الترم الفعال لمستوى معين"""
    today = timezone.now().date()
    semester = Semester.objects.filter(
        level=level, start_date__lte=today, end_date__gte=today
    ).first()
    
    if not semester:
        # إنشاء ترم افتراضي إذا لم يوجد
        semester, _ = Semester.objects.get_or_create(
            term_no=1, level=level,
            defaults={
                'term_name': 'الترم الأول',
                'start_date': timezone.now().date().replace(month=1, day=1),
                'end_date': timezone.now().date().replace(month=6, day=30),
            }
        )
    return semester


def register_student_to_course(student_profile, subject, semester=None):
    """تسجيل الطالب في مقرر معين"""
    if not semester:
        semester = get_active_semester(student_profile.level or subject.level)
        
    if Result.objects.filter(student=student_profile, subject=subject, semester=semester).exists():
        raise ValueError('الطالب مسجل بالفعل في هذا المقرر')
        
    return Result.objects.create(
        student=student_profile,
        subject=subject,
        grade=0,
        semester=semester,
        specialty=student_profile.specialty or subject.specialty,
        level=student_profile.level or subject.level,
        section=student_profile.section or Section.objects.first()
    )


def drop_student_course(student_profile, course_id):
    """إلغاء تسجيل مقرر لطالب"""
    result_record = Result.objects.filter(id=course_id, student=student_profile).first()
    if not result_record:
        raise ValueError('سجل المقرر غير موجود')
    
    sub_name = result_record.subject.sub_name
    result_record.delete()
    return sub_name


def update_student_grades(result_record, attendance_score, activity_score, midterm_score, final_score, reason=''):
    """تحديث درجات الطالب والتأكد من صحتها"""
    try:
        att = float(attendance_score) if attendance_score else 0.0
        act = float(activity_score) if activity_score else 0.0
        mid = float(midterm_score) if midterm_score else 0.0
        fin = float(final_score) if final_score else 0.0
    except ValueError:
        raise ValueError('القيم المدخلة غير صحيحة')
        
    updated = False
    if (result_record.attendance_grade != att or 
        result_record.activity_grade != act or 
        result_record.midterm_grade != mid or 
        result_record.final_grade != fin):
        
        result_record.attendance_grade = att
        result_record.activity_grade = act
        result_record.midterm_grade = mid
        result_record.final_grade = fin
        if reason:
            result_record.edit_reason = reason
        result_record.save()
        updated = True
        
    return updated


def get_department_head_info(section_id):
    """
    استخراج بيانات رئيس القسم، بناءً على الموظف الذي لديه RoleChoices.DEPT_HEAD
    ومرتبط بهذا القسم في managed_section.
    """
    head = EmployeeProfile.objects.filter(
        user__role=RoleChoices.DEPT_HEAD,
        managed_section_id=section_id,
        status='نشط'
    ).first()
    return head
