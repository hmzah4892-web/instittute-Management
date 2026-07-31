"""
خدمات شؤون الطلاب — Student Service Layer
===========================================
تتولى العمليات المتعلقة بالطلاب:
- التسجيل ومتابعة البيانات
- حالة الرسوم والأقساط
- نقل المستوى والتخرج
- أرشيف الخريجين
"""
from django.db.models import Sum, Q
from django.utils import timezone
from institute.models import (
    StudentProfile, Fee, FeePayment, Result,
    Specialty, SLevel, Section, StatusChoices
)


def get_student_full_status(student_profile):
    """
    حالة الطالب الشاملة: أكاديمي + مالي + حضور.
    تُرجع قاموساً يمكن عرضه في لوحة التحكم مباشرة.
    """
    fee_status = student_profile.get_fee_status()
    gpa = student_profile.get_gpa()
    attendance_pct = student_profile.get_attendance_percentage()
    total_penalties = student_profile.get_total_penalties()

    return {
        'profile': student_profile,
        'specialty': student_profile.specialty.spec_name if student_profile.specialty else '—',
        'level': student_profile.level.lev_name if student_profile.level else '—',
        'section': student_profile.section.sec_name if student_profile.section else '—',
        'gpa': gpa,
        'attendance_percentage': attendance_pct,
        'fee_status': fee_status,
        'total_penalties': total_penalties,
        'status': student_profile.status,
    }


def search_students(query, filters=None):
    """
    بحث متقدم في الطلاب.
    filters: dict with optional keys: specialty_id, level_id, section_id, status
    """
    qs = StudentProfile.objects.select_related('user', 'specialty', 'level', 'section')

    if query:
        qs = qs.filter(
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(national_id__icontains=query) |
            Q(user__phone__icontains=query)
        )

    if filters:
        if filters.get('specialty_id'):
            qs = qs.filter(specialty_id=filters['specialty_id'])
        if filters.get('level_id'):
            qs = qs.filter(level_id=filters['level_id'])
        if filters.get('section_id'):
            qs = qs.filter(section_id=filters['section_id'])
        if filters.get('status'):
            qs = qs.filter(status=filters['status'])

    return qs.order_by('-id')


def get_students_with_overdue_fees():
    """قائمة الطلاب المتأخرين عن سداد الأقساط"""
    overdue_fees = Fee.objects.filter(
        remaining__gt=0,
        due_date__lt=timezone.now().date()
    ).select_related('student__user', 'specialty')

    return [{
        'student_name': fee.student.full_name,
        'student_id': fee.student.id,
        'specialty': fee.specialty.spec_name if fee.specialty else '—',
        'total_fees': float(fee.total_fees),
        'paid': float(fee.paid),
        'remaining': float(fee.remaining),
        'due_date': fee.due_date,
        'days_overdue': (timezone.now().date() - fee.due_date).days,
    } for fee in overdue_fees]


def promote_student(student_profile, new_level):
    """نقل طالب إلى مستوى أعلى"""
    old_level = student_profile.level
    student_profile.level = new_level
    student_profile.save(update_fields=['level'])
    return old_level, new_level


def graduate_student(student_profile):
    """
    تخريج الطالب — تغيير حالته إلى 'غير نشط' (خريج).
    """
    student_profile.status = StatusChoices.INACTIVE
    student_profile.save(update_fields=['status'])
    return student_profile


def get_department_students_summary(section=None, specialty=None):
    """إحصائيات الطلاب حسب القسم أو التخصص"""
    qs = StudentProfile.objects.filter(status=StatusChoices.ACTIVE)
    if section:
        qs = qs.filter(section=section)
    if specialty:
        qs = qs.filter(specialty=specialty)

    total = qs.count()
    by_level = {}
    for level in SLevel.objects.all():
        count = qs.filter(level=level).count()
        if count > 0:
            by_level[level.lev_name] = count

    return {
        'total_active': total,
        'by_level': by_level,
    }
