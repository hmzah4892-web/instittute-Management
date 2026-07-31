"""
لوحة تحكم Django Admin
"""
from django.contrib import admin
from .models import (
    User, Subject, Administration, Specialty, Section, SLevel, Semester,
    EmployeeProfile, TeacherProfile, StudentProfile, Parent,
    Fee, FeeDetail, FeePayment, Salary, Expense,
    EmployeeDailyLog, StudentAttendance, Penalty, Message,
    Result, Document, AuditTrail,
    # ✅ النماذج الجديدة:
    ContractType, LeaveRequest, Notification, PayrollRecord,
    CostCenter, AcademicYear, TeacherDailyLog, RoleChoices,
    EmployeeTask
)

# === تسجيل النماذج الأساسية والمستخدمين ===

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'role', 'phone', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'phone')

@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'job_title', 'administration', 'contract_type', 'status')
    list_filter = ('status', 'administration', 'contract_type')
    search_fields = ('user__first_name', 'user__last_name', 'national_id', 'job_title')

@admin.register(EmployeeTask)
class EmployeeTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'employee', 'assigned_date', 'due_date', 'status')
    list_filter = ('status', 'assigned_date', 'due_date')
    search_fields = ('title', 'employee__user__first_name', 'employee__user__last_name')

@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialty', 'contract_type', 'status')
    list_filter = ('status', 'specialty', 'contract_type')
    search_fields = ('user__first_name', 'user__last_name', 'national_id')

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialty', 'level', 'section', 'status')
    list_filter = ('status', 'level', 'section', 'specialty')
    search_fields = ('user__first_name', 'user__last_name', 'national_id')


# === تسجيل الهيكلة الأكاديمية والمراكز ===

@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'is_current')
    list_filter = ('is_current',)

@admin.register(CostCenter)
class CostCenterAdmin(admin.ModelAdmin):
    list_display = ('name', 'center_type', 'monthly_rent', 'is_active')
    list_filter = ('center_type', 'is_active')

admin.site.register(Administration)
admin.site.register(Section)
admin.site.register(SLevel)
admin.site.register(Specialty)
admin.site.register(Semester)
admin.site.register(Subject)


# === تسجيل سجلات الحضور والأداء ===

@admin.register(EmployeeDailyLog)
class EmployeeDailyLogAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'check_in', 'check_out', 'status')
    list_filter = ('status', 'date')

@admin.register(TeacherDailyLog)
class TeacherDailyLogAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'subject', 'date', 'hours_taught')
    list_filter = ('date', 'subject')

@admin.register(StudentAttendance)
class StudentAttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'date', 'status')
    list_filter = ('status', 'date', 'subject')

@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'semester', 'grade', 'is_passed')
    list_filter = ('semester', 'subject')
    search_fields = ('student__user__first_name', 'student__user__last_name')


# === تسجيل الشؤون المالية والرواتب ===

@admin.register(Fee)
class FeeAdmin(admin.ModelAdmin):
    list_display = ('student', 'total_fees', 'paid', 'remaining', 'due_date')
    list_filter = ('due_date',)

@admin.register(PayrollRecord)
class PayrollRecordAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'month', 'year', 'net_salary', 'is_paid')
    list_filter = ('year', 'month', 'is_paid')

admin.site.register(FeePayment)
admin.site.register(Expense)
admin.site.register(Salary)


# === تسجيل الطلبات والإشعارات ===

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('requester', 'leave_type', 'start_date', 'end_date', 'status')
    list_filter = ('status', 'leave_type')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'notif_type', 'sender', 'recipient', 'target_role', 'is_broadcast')
    list_filter = ('notif_type', 'is_broadcast', 'target_role')

admin.site.register(Message)


# === تسجيل الأرشيف والتدقيق ===

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'doc_type', 'uploaded_by', 'created_at')
    list_filter = ('doc_type', 'created_at')

@admin.register(AuditTrail)
class AuditTrailAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'model_name', 'object_id', 'timestamp')
    list_filter = ('action', 'model_name', 'timestamp')
