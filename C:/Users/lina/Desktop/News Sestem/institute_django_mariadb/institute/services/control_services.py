"""
خدمات الكنترول والنتائج — Control Service Layer
=================================================
تتولى العمليات المتعلقة بالامتحانات والنتائج:
- إدخال الدرجات (التقسيم الرباعي)
- احتساب درجة الحضور تلقائياً
- إصدار كشوفات النتائج
- إحصائيات النجاح والرسوب
"""
from django.db.models import Avg, Count, Q, Sum
from institute.models import (
    Result, Subject, StudentProfile, StudentAttendance,
    Semester, Specialty, Section, SLevel,
    StatusChoices, AttendanceStatus
)


def enter_grades_batch(subject, semester, grades_data):
    """
    إدخال أو تحديث درجات مجموعة من الطلاب دفعة واحدة.
    grades_data: list of dicts:
        [{'student_id': int, 'attendance': float, 'activity': float,
          'midterm': float, 'final': float, 'reason': str}, ...]
    Returns: (updated_count, errors)
    """
    updated = 0
    errors = []

    for entry in grades_data:
        try:
            result = Result.objects.get(
                student_id=entry['student_id'],
                subject=subject,
                semester=semester
            )
            result.attendance_grade = min(float(entry.get('attendance', 0)), 10)
            result.activity_grade = min(float(entry.get('activity', 0)), 10)
            result.midterm_grade = min(float(entry.get('midterm', 0)), 20)
            result.final_grade = min(float(entry.get('final', 0)), 60)

            reason = entry.get('reason', '')
            if reason:
                result.edit_reason = reason

            result.save()  # grade is auto-calculated in save()
            updated += 1
        except Result.DoesNotExist:
            errors.append(f"لا يوجد سجل نتيجة للطالب رقم {entry.get('student_id')}")
        except (ValueError, TypeError) as e:
            errors.append(f"خطأ في بيانات الطالب {entry.get('student_id')}: {str(e)}")

    return updated, errors


def auto_calculate_attendance_grades(subject, semester):
    """
    احتساب درجات الحضور تلقائياً لجميع طلاب مقرر معين
    من سجل StudentAttendance.
    درجة الحضور = (عدد الحضور / الإجمالي) × 10
    """
    results = Result.objects.filter(subject=subject, semester=semester)
    updated = 0
    for result in results:
        auto_grade = result.calculate_attendance_grade_auto()
        if result.attendance_grade != auto_grade:
            result.attendance_grade = auto_grade
            result.save()
            updated += 1
    return updated


def get_subject_statistics(subject, semester=None):
    """إحصائيات مقرر: المتوسط، أعلى درجة، أدنى درجة، نسبة النجاح"""
    qs = Result.objects.filter(subject=subject)
    if semester:
        qs = qs.filter(semester=semester)

    if not qs.exists():
        return None

    from django.db.models import Max, Min
    stats = qs.aggregate(
        avg_grade=Avg('grade'),
        max_grade=Max('grade'),
        min_grade=Min('grade'),
        total=Count('result_no'),
        passed=Count('result_no', filter=Q(grade__gte=50)),
        failed=Count('result_no', filter=Q(grade__lt=50)),
    )
    stats['pass_rate'] = round(stats['passed'] / stats['total'] * 100, 1) if stats['total'] > 0 else 0
    stats['avg_grade'] = round(stats['avg_grade'], 2) if stats['avg_grade'] else 0
    return stats


def get_student_transcript(student_profile):
    """كشف درجات شامل لطالب"""
    results = Result.objects.filter(
        student=student_profile
    ).select_related('subject', 'semester', 'specialty').order_by('semester__term_no', 'subject__sub_name')

    transcript = []
    for r in results:
        transcript.append({
            'subject_name': r.subject.sub_name,
            'subject_code': r.subject.sub_no,
            'hours': r.subject.hours,
            'semester': r.semester.term_name if r.semester else '—',
            'attendance_grade': float(r.attendance_grade),
            'activity_grade': float(r.activity_grade),
            'midterm_grade': float(r.midterm_grade),
            'final_grade': float(r.final_grade),
            'grade': float(r.grade),
            'letter_grade': r.letter_grade,
            'is_passed': r.is_passed,
        })

    gpa = student_profile.get_gpa()
    return {'results': transcript, 'gpa': gpa}


def get_semester_results_report(semester, specialty=None):
    """تقرير نتائج ترم معين — اختياري: حسب التخصص"""
    qs = Result.objects.filter(semester=semester)
    if specialty:
        qs = qs.filter(specialty=specialty)

    qs = qs.select_related('student__user', 'subject')

    report = {
        'semester': semester.term_name,
        'total_results': qs.count(),
        'pass_count': qs.filter(grade__gte=50).count(),
        'fail_count': qs.filter(grade__lt=50).count(),
        'average': qs.aggregate(avg=Avg('grade'))['avg'] or 0,
        'students': []
    }

    # تجميع حسب الطالب
    students_data = {}
    for r in qs:
        sid = r.student.id
        if sid not in students_data:
            students_data[sid] = {
                'name': r.student.full_name,
                'subjects': [],
                'total_grade': 0,
                'count': 0,
            }
        students_data[sid]['subjects'].append({
            'subject': r.subject.sub_name,
            'grade': float(r.grade),
            'letter': r.letter_grade,
        })
        students_data[sid]['total_grade'] += float(r.grade)
        students_data[sid]['count'] += 1

    for sid, data in students_data.items():
        data['gpa'] = round(data['total_grade'] / data['count'], 2) if data['count'] > 0 else 0
        report['students'].append(data)

    return report
