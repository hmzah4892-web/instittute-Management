"""
خدمات الموارد البشرية — HR Service Layer
==========================================
تتولى العمليات المتعلقة بالموظفين:
- الحضور والانصراف
- الرواتب والبيانات المالية
- طلبات الإجازة
- محرك الرواتب (Payroll Engine)
- إرسال طلبات للإدارة
"""
from django.utils import timezone
from django.db.models import Sum, Q
from datetime import datetime
from decimal import Decimal
from institute.models import (
    User, EmployeeProfile, TeacherProfile,
    EmployeeDailyLog, TeacherDailyLog, Salary,
    PayrollRecord, LeaveRequest, Message, Notification,
    AttendanceStatus, ContractType, LeaveStatus, NotificationType,
    RoleChoices
)


# ============= الحضور والانصراف =============

def record_employee_attendance(user, action):
    """
    تسجيل حضور أو انصراف الموظف.
    action: 'check_in' أو 'check_out'
    """
    if not hasattr(user, 'employee_profile'):
        raise ValueError("هذا المستخدم ليس موظفاً إدارياً.")

    profile = user.employee_profile
    today = timezone.now().date()
    current_time = timezone.now().time()

    log, created = EmployeeDailyLog.objects.get_or_create(
        employee=profile,
        date=today,
        defaults={'status': AttendanceStatus.PRESENT}
    )

    if action == 'check_in':
        if log.check_in:
            return False, "تم تسجيل الحضور مسبقاً اليوم."
        log.check_in = current_time
        log.save()
        return True, "تم تسجيل الحضور بنجاح."

    elif action == 'check_out':
        if not log.check_in:
            return False, "يجب تسجيل الحضور أولاً."
        if log.check_out:
            return False, "تم تسجيل الانصراف مسبقاً اليوم."
        log.check_out = current_time
        log.save()
        return True, "تم تسجيل الانصراف بنجاح."

    return False, "إجراء غير معروف."


def record_teaching_hours(teacher=None, employee=None, subject=None,
                          hours=1, date=None, notes=''):
    """تسجيل ساعات تدريس لمدرس أو موظف مدرس"""
    if not teacher and not employee:
        raise ValueError("يجب تحديد مدرس أو موظف.")

    log = TeacherDailyLog.objects.create(
        teacher=teacher,
        employee=employee,
        subject=subject,
        date=date or timezone.now().date(),
        hours_taught=hours,
        notes=notes,
    )
    return log


# ============= البيانات المالية =============

def get_employee_financials(user):
    """استرجاع بيانات الراتب والخصميات للموظف"""
    if not hasattr(user, 'employee_profile'):
        return None

    profile = user.employee_profile
    latest_salary = profile.get_latest_salary()

    financials = {
        'contract_type': profile.get_contract_type_display(),
        'basic_salary_amount': float(profile.basic_salary_amount),
        'hourly_rate': float(profile.hourly_rate),
        'total_paid': float(profile.get_total_paid_salary()),
        'latest_salary': float(latest_salary.net_salary) if latest_salary else 0,
        'basic_salary': float(latest_salary.basic_salary) if latest_salary else 0,
        'commission': float(latest_salary.commission) if latest_salary else 0,
        'deductions': float(latest_salary.deductions) if latest_salary else 0,
        'payment_date': latest_salary.payment_date if latest_salary else None,
    }
    return financials


# ============= طلبات الإجازة =============

def submit_leave_request(user, leave_type, start_date, end_date, reason):
    """تقديم طلب إجازة"""
    if end_date < start_date:
        raise ValueError("تاريخ النهاية يجب أن يكون بعد تاريخ البداية.")

    # التحقق من عدم تداخل مع إجازة أخرى
    overlapping = LeaveRequest.objects.filter(
        requester=user,
        status__in=[LeaveStatus.PENDING, LeaveStatus.APPROVED],
    ).filter(
        Q(start_date__lte=end_date, end_date__gte=start_date)
    )
    if overlapping.exists():
        raise ValueError("يوجد طلب إجازة متداخل مع هذه الفترة.")

    leave = LeaveRequest.objects.create(
        requester=user,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
    )

    # إرسال إشعار لقسم الموارد البشرية
    hr_users = User.objects.filter(role=RoleChoices.HR, is_active=True)
    if not hr_users.exists():
        hr_users = User.objects.filter(role=RoleChoices.MANAGER, is_active=True)

    for hr in hr_users:
        Notification.objects.create(
            sender=user,
            recipient=hr,
            title=f"طلب إجازة جديد من {user.full_name}",
            body=f"نوع الإجازة: {leave_type}\nالفترة: {start_date} إلى {end_date}\nالسبب: {reason}",
            notif_type=NotificationType.TASK,
        )

    return leave


def review_leave_request(leave_request_id, reviewer, approved, review_notes=''):
    """مراجعة طلب إجازة (قبول أو رفض)"""
    leave = LeaveRequest.objects.get(request_no=leave_request_id)

    if leave.status != LeaveStatus.PENDING:
        raise ValueError("هذا الطلب تمت مراجعته مسبقاً.")

    leave.status = LeaveStatus.APPROVED if approved else LeaveStatus.REJECTED
    leave.reviewed_by = reviewer
    leave.review_notes = review_notes
    leave.save()

    # إشعار الموظف بالنتيجة
    status_text = "مقبولة ✅" if approved else "مرفوضة ❌"
    Notification.objects.create(
        sender=reviewer,
        recipient=leave.requester,
        title=f"نتيجة طلب الإجازة: {status_text}",
        body=f"تمت مراجعة طلب إجازتك وكانت النتيجة: {status_text}\nملاحظات: {review_notes or 'لا توجد'}",
        notif_type=NotificationType.INFO,
    )

    return leave


def get_pending_leave_requests():
    """قائمة طلبات الإجازة المعلقة"""
    return LeaveRequest.objects.filter(
        status=LeaveStatus.PENDING
    ).select_related('requester').order_by('-created_at')


# ============= محرك الرواتب (Payroll Engine) =============

def generate_payroll(month, year, person_type='employee', person_id=None):
    """
    محرك الرواتب — يولّد كشف الراتب الشهري.
    
    الحساب:
    صافي الراتب = الراتب الأساسي + (أجر الساعة × ساعات التدريس) + مكافآت − خصم غياب − خصومات أخرى
    
    person_type: 'employee' أو 'teacher'
    person_id: None لتوليد كشوف لجميع الأفراد من هذا النوع
    """
    generated = []
    errors = []

    if person_type == 'employee':
        qs = EmployeeProfile.objects.filter(status='نشط')
        if person_id:
            qs = qs.filter(id=person_id)

        for emp in qs:
            try:
                # التحقق من عدم وجود كشف مسبق
                if PayrollRecord.objects.filter(employee=emp, month=month, year=year).exists():
                    errors.append(f"كشف {emp.full_name} موجود مسبقاً لهذا الشهر.")
                    continue

                # حساب مكونات الراتب
                basic = emp.basic_salary_amount
                hourly = emp.hourly_rate
                hours = Decimal(str(emp.get_teaching_hours(month, year)))
                absences = emp.get_absence_count(month, year)

                # خصم الغياب: (الراتب اليومي × أيام الغياب)
                daily_rate = basic / 30 if basic > 0 else Decimal('0')
                absence_deduction = daily_rate * absences

                record = PayrollRecord.objects.create(
                    employee=emp,
                    month=month,
                    year=year,
                    basic_salary=basic,
                    teaching_hours=hours,
                    hourly_rate=hourly,
                    absence_days=absences,
                    absence_deduction=absence_deduction,
                )
                generated.append(record)
            except Exception as e:
                errors.append(f"خطأ في كشف {emp.full_name}: {str(e)}")

    elif person_type == 'teacher':
        qs = TeacherProfile.objects.filter(status='نشط')
        if person_id:
            qs = qs.filter(id=person_id)

        for teacher in qs:
            try:
                if PayrollRecord.objects.filter(teacher=teacher, month=month, year=year).exists():
                    errors.append(f"كشف {teacher.full_name} موجود مسبقاً لهذا الشهر.")
                    continue

                hours = Decimal(str(teacher.get_teaching_hours(month, year)))
                hourly = teacher.hourly_rate

                record = PayrollRecord.objects.create(
                    teacher=teacher,
                    month=month,
                    year=year,
                    basic_salary=Decimal('0'),
                    teaching_hours=hours,
                    hourly_rate=hourly,
                )
                generated.append(record)
            except Exception as e:
                errors.append(f"خطأ في كشف {teacher.full_name}: {str(e)}")

    return generated, errors


def get_payroll_summary(month, year):
    """ملخص كشوف الرواتب لشهر معين"""
    records = PayrollRecord.objects.filter(month=month, year=year)
    total_basic = records.aggregate(t=Sum('basic_salary'))['t'] or 0
    total_teaching = records.aggregate(t=Sum('teaching_pay'))['t'] or 0
    total_deductions = records.aggregate(t=Sum('absence_deduction'))['t'] or 0
    total_net = records.aggregate(t=Sum('net_salary'))['t'] or 0
    total_paid = records.filter(is_paid=True).count()
    total_unpaid = records.filter(is_paid=False).count()

    return {
        'month': month,
        'year': year,
        'total_records': records.count(),
        'total_basic': float(total_basic),
        'total_teaching_pay': float(total_teaching),
        'total_deductions': float(total_deductions),
        'total_net_salary': float(total_net),
        'paid_count': total_paid,
        'unpaid_count': total_unpaid,
    }


def mark_payroll_as_paid(payroll_id):
    """تسجيل صرف كشف الراتب"""
    record = PayrollRecord.objects.get(payroll_no=payroll_id)
    record.is_paid = True
    record.paid_date = timezone.now().date()
    record.save(update_fields=['is_paid', 'paid_date'])
    return record


# ============= طلبات الموارد البشرية =============

def submit_hr_request(sender_user, subject, body):
    """رفع طلب (إجازة، سلفة، قرطاسية، إلخ) إلى قسم الموارد البشرية"""
    hr_users = User.objects.filter(role='hr')
    if not hr_users.exists():
        # إذا لم يوجد موظف HR، نرسل للمدير
        hr_users = User.objects.filter(role='manager')

    if not hr_users.exists():
        raise ValueError("لا يوجد أي موظف موارد بشرية أو مدير لاستقبال الطلب.")

    # إرسال رسالة لكل موظفي الموارد البشرية
    for hr in hr_users:
        Message.objects.create(
            sender=sender_user,
            receiver=hr,
            subject=f"[طلب موظف] {subject}",
            body=body
        )
    return True
