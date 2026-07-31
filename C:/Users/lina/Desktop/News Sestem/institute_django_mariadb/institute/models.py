from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models import Sum, Avg, Count, Q


# ============================================================
#  ثوابت الخيارات (Choices) — مركزية وسهلة الصيانة
# ============================================================

class RoleChoices(models.TextChoices):
    MANAGER        = 'manager',        'مدير عام'
    ADMIN          = 'admin',          'مسؤول النظام'
    FACULTY        = 'faculty',        'عضو هيئة تدريس'
    STUDENT        = 'student',        'طالب'
    ADMISSION      = 'admission',      'قبول وتسجيل'
    FINANCE        = 'finance',        'شؤون مالية'
    STAFF          = 'staff',          'موظف إداري'
    HR             = 'hr',             'شؤون الموظفين'
    CONTROL        = 'control',        'كنترول'
    DEPT_HEAD      = 'dept_head',      'رئيس قسم'


class GenderChoices(models.TextChoices):
    MALE   = 'ذكر',  'ذكر'
    FEMALE = 'أنثى', 'أنثى'


class StatusChoices(models.TextChoices):
    ACTIVE   = 'نشط',    'نشط'
    INACTIVE = 'غير نشط', 'غير نشط'
    ON_LEAVE = 'إجازة',  'إجازة'


class AttendanceStatus(models.TextChoices):
    PRESENT = 'حاضر', 'حاضر'
    ABSENT  = 'غائب', 'غائب'
    EXCUSED = 'بعذر', 'بعذر'


class ExpenseType(models.TextChoices):
    RENT_FLOOR1       = 'rent_floor1',       'إيجار الطابق الأول (إداري)'
    RENT_FLOOR2       = 'rent_floor2',       'إيجار الطابق الثاني (طبي)'
    DAILY_WITHDRAWAL  = 'daily_withdrawal',  'سحب يومي للموظفين'
    STATIONERY        = 'stationery',        'قرطاسية ومستلزمات'
    UTILITIES         = 'utilities',         'كهرباء وماء'
    MAINTENANCE       = 'maintenance',       'صيانة'
    GENERAL           = 'general',           'مصاريف تشغيلية عامة'


class DocumentType(models.TextChoices):
    CONTRACT     = 'contract',     'عقد'
    ID_CARD      = 'id_card',      'بطاقة هوية'
    CERTIFICATE  = 'certificate',  'شهادة / مؤهل'
    PHOTO        = 'photo',        'صورة شخصية'
    OTHER        = 'other',        'أخرى'


class PenaltyType(models.TextChoices):
    ABSENCE      = 'absence',      'غياب'
    LATE         = 'late',         'تأخر'
    BEHAVIOR     = 'behavior',     'سلوك'
    FINANCIAL    = 'financial',    'مالية'
    OTHER        = 'other',        'أخرى'


class AuditAction(models.TextChoices):
    CREATE = 'create', 'إضافة'
    UPDATE = 'update', 'تعديل'
    DELETE = 'delete', 'حذف'
    VIEW   = 'view',   'فتح / عرض'
    LOGIN  = 'login',  'تسجيل دخول'
    LOGOUT = 'logout', 'تسجيل خروج'


class ContractType(models.TextChoices):
    """أنواع العقود الوظيفية"""
    FIXED_SALARY    = 'fixed',    'راتب ثابت فقط'
    HOURLY_CONTRACT = 'hourly',   'تعاقد بالساعة/المحاضرة فقط'
    MIXED           = 'mixed',    'راتب ثابت + تدريس بالساعة'


class LeaveStatus(models.TextChoices):
    """حالات طلبات الإجازة"""
    PENDING  = 'pending',  'بانتظار الموافقة'
    APPROVED = 'approved', 'مقبولة'
    REJECTED = 'rejected', 'مرفوضة'


class NotificationType(models.TextChoices):
    """أنواع الإشعارات"""
    INFO      = 'info',      'معلومات'
    WARNING   = 'warning',   'تحذير'
    ALERT     = 'alert',     'إنذار'
    CIRCULAR  = 'circular',  'تعميم'
    TASK      = 'task',      'مهمة'


class CostCenterType(models.TextChoices):
    """أنواع مراكز التكلفة"""
    FLOOR1_ADMIN  = 'floor1', 'الطابق الأول (أقسام إدارية)'
    FLOOR2_MEDICAL = 'floor2', 'الطابق الثاني (أقسام طبية)'
    GENERAL        = 'general', 'عام'


# ============================================================
#  المستخدم (User)
# ============================================================

class User(AbstractUser):
    """نموذج المستخدم المخصص مع دعم الأدوار الموحدة"""
    role  = models.CharField(max_length=20, choices=RoleChoices.choices, default=RoleChoices.STUDENT, verbose_name="الدور")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="رقم الهاتف")

    class Meta:
        verbose_name        = 'مستخدم'
        verbose_name_plural = 'المستخدمون'
        indexes = [
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    # خصائص مساعدة للتحقق من الدور بسرعة
    @property
    def is_manager(self):
        return self.role == RoleChoices.MANAGER

    @property
    def is_faculty(self):
        return self.role == RoleChoices.FACULTY

    @property
    def is_student_role(self):
        return self.role == RoleChoices.STUDENT

    @property
    def is_finance(self):
        return self.role == RoleChoices.FINANCE

    @property
    def is_admission(self):
        return self.role == RoleChoices.ADMISSION

    @property
    def is_hr(self):
        return self.role == RoleChoices.HR

    @property
    def full_name(self):
        return self.get_full_name() or self.username


# ============================================================
#  الهياكل الأساسية (Foundation Tables)
# ============================================================

class SLevel(models.Model):
    """جدول المستويات الدراسية"""
    lev_no   = models.IntegerField(primary_key=True, verbose_name="رقم المستوى")
    lev_name = models.CharField(max_length=50, unique=True, verbose_name="اسم المستوى")

    class Meta:
        verbose_name        = "مستوى دراسي"
        verbose_name_plural = "المستويات الدراسية"
        ordering            = ['lev_no']

    def __str__(self):
        return self.lev_name


class Section(models.Model):
    """جدول الأقسام الرئيسية (إداري / طبي)"""
    sec_no   = models.IntegerField(primary_key=True, verbose_name="رقم القسم")
    sec_name = models.CharField(max_length=50, unique=True, verbose_name="اسم القسم")

    class Meta:
        verbose_name        = "قسم عام"
        verbose_name_plural = "الأقسام العامة"
        ordering            = ['sec_no']

    def __str__(self):
        return self.sec_name


class Specialty(models.Model):
    """جدول التخصصات — يرتبط بالمستوى والقسم"""
    spec_no   = models.IntegerField(primary_key=True, verbose_name="رقم التخصص")
    spec_name = models.CharField(max_length=100, verbose_name="اسم التخصص")
    level     = models.ForeignKey(SLevel, on_delete=models.CASCADE, related_name="specialties", verbose_name="المستوى")
    section   = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="specialties", verbose_name="القسم")
    # رسوم التخصص الافتراضية (حسب متطلبات المعهد: 75000 إداري / 125000 طبي)
    default_fees = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name="الرسوم الدراسية الافتراضية",
        help_text="رسوم التخصص القياسية (75000 إداري / 125000 طبي)"
    )

    class Meta:
        verbose_name        = "تخصص"
        verbose_name_plural = "التخصصات"
        ordering            = ['spec_no']
        indexes = [
            models.Index(fields=['section']),
            models.Index(fields=['level']),
        ]

    def __str__(self):
        return f"{self.spec_name} ({self.level.lev_name})"

    def get_active_students_count(self):
        """عدد الطلاب النشطين في هذا التخصص"""
        return self.student_profiles.filter(status=StatusChoices.ACTIVE).count()

    def get_total_revenue(self):
        """إجمالي الرسوم المحصلة من طلاب هذا التخصص"""
        return self.fees.aggregate(total=Sum('paid'))['total'] or 0


class Administration(models.Model):
    """جدول الإدارات والأقسام التنظيمية"""
    admin_no      = models.IntegerField(primary_key=True, verbose_name="رقم الإدارة")
    admin_name    = models.CharField(max_length=100, verbose_name="اسم الإدارة")
    admin_type    = models.CharField(max_length=50, verbose_name="نوع الإدارة")
    manager_name  = models.CharField(max_length=100, blank=True, null=True, verbose_name="اسم المسؤول الإداري")
    contact_info  = models.CharField(max_length=100, blank=True, null=True, verbose_name="بيانات التواصل")
    status        = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE, verbose_name="الحالة")
    address       = models.CharField(max_length=150, blank=True, null=True, verbose_name="العنوان")
    notes         = models.TextField(blank=True, null=True, verbose_name="ملاحظات")

    class Meta:
        verbose_name        = "إدارة"
        verbose_name_plural = "الإدارات"
        ordering            = ['admin_no']

    def __str__(self):
        return self.admin_name


# ============================================================
#  الملفات الشخصية (Profiles)
# ============================================================

class EmployeeProfile(models.Model):
    """جدول الموظفين الإداريين"""
    user           = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role__in': [RoleChoices.MANAGER, RoleChoices.ADMIN,
                                        RoleChoices.ADMISSION, RoleChoices.FINANCE,
                                        RoleChoices.STAFF, RoleChoices.HR,
                                        RoleChoices.CONTROL, RoleChoices.DEPT_HEAD]},
        related_name='employee_profile',
        verbose_name="المستخدم"
    )
    emp_address    = models.CharField(max_length=150, blank=True, null=True, verbose_name="العنوان")
    qualification  = models.CharField(max_length=100, blank=True, null=True, verbose_name="المؤهل العلمي")
    gender         = models.CharField(max_length=10, choices=GenderChoices.choices, verbose_name="الجنس")
    hire_date      = models.DateField(verbose_name="تاريخ التوظيف")
    end_date       = models.DateField(blank=True, null=True, verbose_name="تاريخ إنهاء التوظيف")
    status         = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE, verbose_name="الحالة")
    administration = models.ForeignKey(Administration, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name="employees", verbose_name="الإدارة التابع لها")
    job_title      = models.CharField(max_length=50, verbose_name="المسمى الوظيفي")
    national_id    = models.CharField(max_length=20, blank=True, null=True, unique=True, verbose_name="رقم الهوية الوطنية")
    # ✅ حقول جديدة لدعم نظام العقود المتعدد
    contract_type  = models.CharField(
        max_length=20, choices=ContractType.choices,
        default=ContractType.FIXED_SALARY, verbose_name="نوع العقد"
    )
    basic_salary_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name="الراتب الأساسي الشهري",
        help_text="الراتب الثابت الشهري (صفر إذا تعاقد بالساعة فقط)"
    )
    hourly_rate    = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name="أجر الساعة/المحاضرة",
        help_text="أجر كل ساعة تدريس (صفر إذا راتب ثابت فقط)"
    )
    # ربط الموظف بالقسم الأكاديمي الذي يرأسه (إن كان رئيس قسم)
    managed_section = models.ForeignKey(
        'Section', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='head_employees', verbose_name="القسم المُدار (لرئيس القسم)"
    )

    class Meta:
        verbose_name        = "ملف موظف"
        verbose_name_plural = "ملفات الموظفين"
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['administration']),
            models.Index(fields=['contract_type']),
        ]

    def __str__(self):
        return f"{self.user.full_name} — {self.job_title}"

    @property
    def full_name(self):
        return self.user.full_name

    @property
    def is_teaching_eligible(self):
        """هل هذا الموظف مؤهل للتدريس (عقد مختلط)؟"""
        return self.contract_type == ContractType.MIXED

    def get_latest_salary(self):
        """آخر راتب مسجل للموظف"""
        return self.salaries.order_by('-payment_date').first()

    def get_total_paid_salary(self):
        """إجمالي الرواتب المدفوعة"""
        return self.salaries.aggregate(total=Sum('net_salary'))['total'] or 0

    def get_teaching_hours(self, month=None, year=None):
        """عدد ساعات التدريس في شهر معين (للموظف ذو العقد المختلط)"""
        from .models import TeacherDailyLog
        qs = TeacherDailyLog.objects.filter(employee=self)
        if month and year:
            qs = qs.filter(date__month=month, date__year=year)
        return qs.aggregate(total=Sum('hours_taught'))['total'] or 0

    def get_absence_count(self, month=None, year=None):
        """عدد أيام الغياب في شهر معين"""
        from django.utils import timezone
        qs = self.daily_logs.filter(status=AttendanceStatus.ABSENT)
        if month and year:
            qs = qs.filter(date__month=month, date__year=year)
        return qs.count()


class TeacherProfile(models.Model):
    """جدول المدرسين — مرتبط بالراتب عبر FK حقيقي"""
    user          = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': RoleChoices.FACULTY},
        related_name='teacher_profile',
        verbose_name="المستخدم"
    )
    specialty      = models.ForeignKey(Specialty, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name="teachers", verbose_name="التخصص")
    qualification  = models.CharField(max_length=100, blank=True, null=True, verbose_name="المؤهل العلمي")
    contract_date  = models.DateField(verbose_name="تاريخ التعاقد")
    contract_end   = models.DateField(blank=True, null=True, verbose_name="تاريخ انتهاء العقد")
    status         = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE, verbose_name="الحالة")
    national_id    = models.CharField(max_length=20, blank=True, null=True, unique=True, verbose_name="رقم الهوية")
    # ✅ إصلاح: salary كـ ForeignKey حقيقي بدلاً من IntegerField
    salary         = models.ForeignKey(
        'Salary',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="instructors",
        verbose_name="سجل الراتب"
    )
    # ✅ حقول جديدة لدعم نظام العقود
    contract_type  = models.CharField(
        max_length=20, choices=ContractType.choices,
        default=ContractType.HOURLY_CONTRACT, verbose_name="نوع العقد"
    )
    hourly_rate    = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name="أجر الساعة/المحاضرة",
        help_text="أجر كل ساعة/محاضرة تدريس"
    )

    class Meta:
        verbose_name        = "ملف مدرس"
        verbose_name_plural = "ملفات المدرسين"
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['specialty']),
            models.Index(fields=['contract_type']),
        ]

    def __str__(self):
        return self.user.full_name

    @property
    def full_name(self):
        return self.user.full_name

    def get_subjects_count(self):
        """عدد المقررات التي يدرسها"""
        return self.subjects.count()

    def get_active_students_count(self):
        """عدد الطلاب الذين يتلقون دروساً منه"""
        return StudentProfile.objects.filter(
            specialty=self.specialty,
            status=StatusChoices.ACTIVE
        ).count()

    def is_contract_active(self):
        """هل العقد لا يزال سارياً؟"""
        if not self.contract_end:
            return True
        return self.contract_end >= timezone.now().date()

    def get_teaching_hours(self, month=None, year=None):
        """عدد ساعات التدريس في شهر معين"""
        qs = self.lecture_logs.all()
        if month and year:
            qs = qs.filter(date__month=month, date__year=year)
        return qs.aggregate(total=Sum('hours_taught'))['total'] or 0

    def calculate_monthly_pay(self, month=None, year=None):
        """حساب المستحقات الشهرية"""
        hours = self.get_teaching_hours(month, year)
        return hours * self.hourly_rate


class StudentProfile(models.Model):
    """جدول الطلاب"""
    user          = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': RoleChoices.STUDENT},
        related_name='student_profile',
        verbose_name="المستخدم"
    )
    st_address    = models.CharField(max_length=150, blank=True, null=True, verbose_name="عنوان الطالب")
    qualification = models.CharField(max_length=100, blank=True, null=True, verbose_name="المؤهل السابق")
    parent_phone  = models.CharField(max_length=20, blank=True, null=True, verbose_name="رقم ولي الأمر")
    specialty     = models.ForeignKey(Specialty, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name="student_profiles", verbose_name="التخصص")
    level         = models.ForeignKey(SLevel, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name="students", verbose_name="المستوى")
    gender        = models.CharField(max_length=10, choices=GenderChoices.choices, verbose_name="الجنس")
    section       = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name="students", verbose_name="القسم")
    status        = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE, verbose_name="الحالة")
    birth_date    = models.DateField(blank=True, null=True, verbose_name="تاريخ الميلاد")
    national_id   = models.CharField(max_length=20, blank=True, null=True, unique=True, verbose_name="رقم الهوية")
    enrollment_date = models.DateField(default=timezone.now, verbose_name="تاريخ التسجيل")

    class Meta:
        verbose_name        = "ملف طالب"
        verbose_name_plural = "ملفات الطلاب"
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['specialty']),
            models.Index(fields=['level']),
            models.Index(fields=['section']),
        ]

    def __str__(self):
        return self.user.full_name

    @property
    def full_name(self):
        return self.user.full_name

    def get_attendance_percentage(self, subject=None):
        """
        نسبة الحضور للطالب.
        إن أُعطي subject فقط لذلك المقرر، وإلا لكل المقررات.
        """
        qs = self.attendances.all()
        if subject:
            qs = qs.filter(subject=subject)
        total   = qs.count()
        present = qs.filter(status=AttendanceStatus.PRESENT).count()
        return round((present / total * 100), 1) if total > 0 else 0.0

    def get_gpa(self):
        """المعدل التراكمي للطالب (متوسط الدرجات الكلية)"""
        avg = self.results.aggregate(gpa=Avg('grade'))['gpa']
        return round(avg, 2) if avg else 0.0

    def get_fee_status(self):
        """حالة الرسوم الدراسية للطالب"""
        fee = self.fees.filter(level=self.level, specialty=self.specialty).first()
        if not fee:
            return {'status': 'لا يوجد سجل رسوم', 'remaining': 0, 'paid': 0}
        return {
            'status':    'مكتمل' if fee.remaining <= 0 else 'متبقي',
            'remaining': fee.remaining,
            'paid':      fee.paid,
            'total':     fee.total_fees,
        }

    def get_total_penalties(self):
        """إجمالي الغرامات المترتبة على الطالب"""
        return self.penalties.aggregate(total=Sum('amount'))['total'] or 0


class Parent(models.Model):
    """جدول أولياء الأمور"""
    parent_phone   = models.CharField(max_length=20, primary_key=True, verbose_name="رقم ولي الأمر")
    parent_name    = models.CharField(max_length=100, verbose_name="اسم ولي الأمر")
    parent_address = models.CharField(max_length=150, blank=True, null=True, verbose_name="عنوان ولي الأمر")
    student        = models.ForeignKey(StudentProfile, on_delete=models.CASCADE,
                                       related_name="parents", verbose_name="الطالب")
    relationship   = models.CharField(max_length=50, verbose_name="صلة القرابة (أب/أم/إلخ)")

    class Meta:
        verbose_name        = "ولي أمر"
        verbose_name_plural = "أولياء الأمور"

    def __str__(self):
        return f"{self.parent_name} ({self.relationship}) — {self.student.full_name}"


# ============================================================
#  المقررات والفصول الدراسية
# ============================================================

class Semester(models.Model):
    """جدول الأترام الدراسية"""
    term_no    = models.IntegerField(primary_key=True, verbose_name="رقم الترم")
    term_name  = models.CharField(max_length=50, verbose_name="اسم الترم")
    # ✅ إصلاح: تحويل من IntegerField إلى DateField
    start_date = models.DateField(verbose_name="تاريخ بداية الترم")
    end_date   = models.DateField(verbose_name="تاريخ نهاية الترم")
    level      = models.ForeignKey(SLevel, on_delete=models.CASCADE,
                                   related_name="semesters", verbose_name="المستوى")

    class Meta:
        verbose_name        = "ترم دراسي"
        verbose_name_plural = "الأتـرام الدراسية"
        ordering            = ['term_no']

    def __str__(self):
        return f"{self.term_name} ({self.level.lev_name})"

    @property
    def is_active(self):
        """هل الترم جارٍ الآن؟"""
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date

    @property
    def duration_weeks(self):
        """عدد أسابيع الترم"""
        return (self.end_date - self.start_date).days // 7


class Subject(models.Model):
    """جدول المقررات الدراسية"""
    sub_no    = models.IntegerField(primary_key=True, verbose_name="رقم المقرر")
    sub_name  = models.CharField(max_length=100, verbose_name="اسم المقرر")
    hours     = models.IntegerField(default=2, validators=[MinValueValidator(1), MaxValueValidator(10)],
                                    verbose_name="عدد الساعات الأسبوعية")
    level     = models.ForeignKey(SLevel, on_delete=models.CASCADE,
                                  related_name="subjects", verbose_name="المستوى")
    specialty = models.ForeignKey(Specialty, on_delete=models.CASCADE,
                                  related_name="subjects", verbose_name="التخصص")
    teacher   = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name="subjects", verbose_name="المدرس")
    semester  = models.ForeignKey(Semester, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name="subjects", verbose_name="الترم")
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    class Meta:
        verbose_name        = "مقرر دراسي"
        verbose_name_plural = "المقررات الدراسية"
        ordering            = ['sub_no']
        indexes = [
            models.Index(fields=['specialty', 'level']),
            models.Index(fields=['teacher']),
        ]

    def __str__(self):
        return f"{self.sub_name} ({self.specialty.spec_name})"

    def get_enrolled_count(self):
        """عدد الطلاب المسجلين في هذا المقرر"""
        return StudentProfile.objects.filter(
            specialty=self.specialty,
            level=self.level,
            status=StatusChoices.ACTIVE
        ).count()

    def get_average_grade(self):
        """متوسط درجات هذا المقرر"""
        avg = self.results.aggregate(avg=Avg('grade'))['avg']
        return round(avg, 2) if avg else 0.0

    def get_pass_rate(self):
        """نسبة النجاح في المقرر (درجة >= 50)"""
        total = self.results.count()
        if total == 0:
            return 0.0
        passed = self.results.filter(grade__gte=50).count()
        return round(passed / total * 100, 1)


# ============================================================
#  الحضور والغياب
# ============================================================

class StudentAttendance(models.Model):
    """جدول تحضير الطلاب"""
    student   = models.ForeignKey(StudentProfile, on_delete=models.CASCADE,
                                  related_name="attendances", verbose_name="الطالب")
    subject   = models.ForeignKey(Subject, on_delete=models.CASCADE,
                                  related_name="attendances", verbose_name="المقرر")
    date      = models.DateField(verbose_name="التاريخ")
    status    = models.CharField(max_length=20, choices=AttendanceStatus.choices,
                                 default=AttendanceStatus.PRESENT, verbose_name="الحالة")
    teacher   = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name="student_attendances", verbose_name="المدرس المسجِّل")
    specialty = models.ForeignKey(Specialty, on_delete=models.CASCADE,
                                  related_name="attendances", verbose_name="التخصص")
    notes     = models.CharField(max_length=200, blank=True, null=True, verbose_name="ملاحظات")

    class Meta:
        verbose_name        = "تحضير طالب"
        verbose_name_plural = "تحضير الطلاب"
        unique_together     = ('student', 'subject', 'date')
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['student', 'subject']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.student.full_name} — {self.subject.sub_name} ({self.date}) [{self.status}]"


class EmployeeDailyLog(models.Model):
    """جدول يوميات حضور الموظفين"""
    employee  = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE,
                                  related_name="daily_logs", verbose_name="الموظف")
    date      = models.DateField(default=timezone.now, verbose_name="التاريخ")
    check_in  = models.TimeField(blank=True, null=True, verbose_name="وقت الحضور")
    check_out = models.TimeField(blank=True, null=True, verbose_name="وقت المغادرة")
    status    = models.CharField(max_length=20, choices=AttendanceStatus.choices,
                                 default=AttendanceStatus.PRESENT, verbose_name="الحالة")
    notes     = models.CharField(max_length=200, blank=True, null=True, verbose_name="ملاحظات")

    class Meta:
        verbose_name        = "يومية موظف"
        verbose_name_plural = "يوميات الموظفين"
        unique_together     = ('employee', 'date')
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.employee.full_name} ({self.date}) — {self.status}"

    @property
    def worked_hours(self):
        """عدد ساعات العمل الفعلية"""
        if self.check_in and self.check_out:
            from datetime import datetime, date
            t_in  = datetime.combine(date.today(), self.check_in)
            t_out = datetime.combine(date.today(), self.check_out)
            delta = t_out - t_in
            return round(delta.seconds / 3600, 2)
        return 0.0


# ============================================================
#  النظام المالي
# ============================================================

class Salary(models.Model):
    """جدول الرواتب — يدعم الموظفين والمدرسين مع ربط بالتخصص والقسم"""
    salary_no    = models.AutoField(primary_key=True, verbose_name="رقم الراتب")
    employee     = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE,
                                     related_name="salaries", verbose_name="الموظف",
                                     null=True, blank=True)
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2,
                                       validators=[MinValueValidator(0)],
                                       verbose_name="الراتب الأساسي")
    commission   = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                       validators=[MinValueValidator(0)],
                                       verbose_name="العمولة / المكافأة")
    deductions   = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                       validators=[MinValueValidator(0)],
                                       verbose_name="الخصومات")
    net_salary   = models.DecimalField(max_digits=10, decimal_places=2,
                                       verbose_name="صافي الراتب")
    # ✅ إصلاح: تحويل من IntegerField إلى DateField
    payment_date = models.DateField(default=timezone.now, verbose_name="تاريخ الصرف")
    # ✅ إضافة جديدة من ERD: ربط الراتب بالتخصص والقسم
    specialty    = models.ForeignKey(Specialty, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name="salaries", verbose_name="التخصص المرتبط")
    section      = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name="salaries", verbose_name="القسم المرتبط")
    notes        = models.CharField(max_length=200, blank=True, null=True, verbose_name="ملاحظات")

    class Meta:
        verbose_name        = "راتب"
        verbose_name_plural = "الرواتب"
        ordering            = ['-payment_date']
        indexes = [
            models.Index(fields=['payment_date']),
            models.Index(fields=['section']),
        ]

    def save(self, *args, **kwargs):
        # حساب صافي الراتب تلقائياً
        self.net_salary = self.basic_salary + self.commission - self.deductions
        super().save(*args, **kwargs)

    def __str__(self):
        recipient = self.employee.full_name if self.employee else "غير محدد"
        return f"راتب {recipient} — {self.net_salary:,.0f} ({self.payment_date})"


class Penalty(models.Model):
    """جدول الغرامات والعقوبات"""
    penalty_no   = models.AutoField(primary_key=True, verbose_name="رقم الغرامة")
    penalty_type = models.CharField(max_length=50, choices=PenaltyType.choices,
                                    default=PenaltyType.OTHER, verbose_name="نوع الغرامة")
    reason       = models.TextField(verbose_name="سبب الغرامة")
    # ✅ إصلاح: تحويل من IntegerField إلى DateField
    date         = models.DateField(default=timezone.now, verbose_name="تاريخ الغرامة")
    student      = models.ForeignKey(StudentProfile, on_delete=models.CASCADE,
                                     related_name="penalties", verbose_name="الطالب")
    amount       = models.DecimalField(max_digits=10, decimal_places=2,
                                       validators=[MinValueValidator(0)],
                                       verbose_name="مبلغ الغرامة")
    is_paid      = models.BooleanField(default=False, verbose_name="مدفوعة؟")
    employee     = models.ForeignKey(EmployeeProfile, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name="issued_penalties", verbose_name="الموظف المُصدِر")
    teacher      = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name="issued_penalties", verbose_name="المدرس المُصدِر")

    class Meta:
        verbose_name        = "غرامة / عقوبة"
        verbose_name_plural = "الغرامات والعقوبات"
        ordering            = ['-date']
        indexes = [
            models.Index(fields=['student']),
            models.Index(fields=['is_paid']),
        ]

    def __str__(self):
        return f"{self.get_penalty_type_display()} — {self.student.full_name} ({self.amount:,.0f})"


class Fee(models.Model):
    """جدول الرسوم الدراسية للطلاب"""
    fee_no      = models.AutoField(primary_key=True, verbose_name="رقم حساب الرسوم")
    student     = models.ForeignKey(StudentProfile, on_delete=models.CASCADE,
                                    related_name="fees", verbose_name="الطالب")
    specialty   = models.ForeignKey(Specialty, on_delete=models.CASCADE,
                                    related_name="fees", verbose_name="التخصص")
    level       = models.ForeignKey(SLevel, on_delete=models.CASCADE,
                                    related_name="fees", verbose_name="المستوى")
    total_fees  = models.DecimalField(max_digits=10, decimal_places=2,
                                      validators=[MinValueValidator(0)],
                                      verbose_name="الرسوم الكلية")
    paid        = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                      verbose_name="إجمالي المدفوع")
    remaining   = models.DecimalField(max_digits=10, decimal_places=2,
                                      verbose_name="المتبقي")
    # ✅ إصلاح: تحويل من IntegerField إلى DateField
    due_date    = models.DateField(verbose_name="آخر موعد للسداد")
    created_at  = models.DateField(default=timezone.now, verbose_name="تاريخ فتح الحساب")

    class Meta:
        verbose_name        = "حساب رسوم"
        verbose_name_plural = "حسابات الرسوم"
        unique_together     = ('student', 'specialty', 'level')
        indexes = [
            models.Index(fields=['student']),
            models.Index(fields=['specialty']),
        ]

    def save(self, *args, **kwargs):
        # إعادة حساب المتبقي تلقائياً
        self.remaining = self.total_fees - self.paid
        super().save(*args, **kwargs)

    def __str__(self):
        return f"رسوم {self.student.full_name} — المتبقي: {self.remaining:,.0f}"

    @property
    def is_fully_paid(self):
        return self.remaining <= 0

    @property
    def payment_percentage(self):
        """نسبة ما تم سداده"""
        if self.total_fees == 0:
            return 0.0
        return round(float(self.paid) / float(self.total_fees) * 100, 1)


class FeeDetail(models.Model):
    """تفاصيل تصنيف الرسوم (تنسيق، أنشطة، دراسة، غرامات)"""
    fee              = models.OneToOneField(Fee, on_delete=models.CASCADE,
                                            primary_key=True, related_name="details", verbose_name="حساب الرسوم")
    coordination_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                           validators=[MinValueValidator(0)], verbose_name="رسوم التنسيق")
    activity_fee     = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                           validators=[MinValueValidator(0)], verbose_name="رسوم الأنشطة")
    tuition_fee      = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                           validators=[MinValueValidator(0)], verbose_name="رسوم الدراسة")
    fine             = models.ForeignKey(Penalty, on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name="fee_details", verbose_name="الغرامة المرتبطة")

    class Meta:
        verbose_name        = "تفاصيل الرسوم"
        verbose_name_plural = "تفاصيل الرسوم"

    def __str__(self):
        return f"تفاصيل رسوم: {self.fee.student.full_name}"

    @property
    def calculated_total(self):
        """مجموع التفاصيل المحسوبة"""
        penalty_amount = self.fine.amount if self.fine else 0
        return self.coordination_fee + self.activity_fee + self.tuition_fee + penalty_amount


class FeePayment(models.Model):
    """جدول أقساط الدفع — تتبع كل دفعة بشكل منفصل"""
    payment_no   = models.AutoField(primary_key=True, verbose_name="رقم القسط")
    fee          = models.ForeignKey(Fee, on_delete=models.CASCADE,
                                     related_name="payments", verbose_name="حساب الرسوم")
    amount_paid  = models.DecimalField(max_digits=10, decimal_places=2,
                                       validators=[MinValueValidator(0.01)],
                                       verbose_name="المبلغ المدفوع")
    payment_date = models.DateField(default=timezone.now, verbose_name="تاريخ الدفع")
    receipt_no   = models.CharField(max_length=50, unique=True, verbose_name="رقم سند القبض")
    received_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                     related_name="received_payments", verbose_name="الموظف المستلم")
    notes        = models.CharField(max_length=200, blank=True, null=True, verbose_name="ملاحظات")

    class Meta:
        verbose_name        = "قسط رسوم"
        verbose_name_plural = "أقساط الرسوم"
        ordering            = ['-payment_date']
        indexes = [
            models.Index(fields=['fee']),
            models.Index(fields=['payment_date']),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # تحديث إجمالي المدفوع والمتبقي في Fee تلقائياً
        fee = self.fee
        total_paid  = fee.payments.aggregate(total=Sum('amount_paid'))['total'] or 0
        fee.paid    = total_paid
        fee.remaining = fee.total_fees - fee.paid
        fee.save(update_fields=['paid', 'remaining'])

    def __str__(self):
        return f"قسط {self.fee.student.full_name} — {self.amount_paid:,.0f} (سند: {self.receipt_no})"


class Expense(models.Model):
    """جدول المصروفات والمسحوبات التشغيلية اليومية"""
    expense_no   = models.AutoField(primary_key=True, verbose_name="رقم المصروف")
    expense_type = models.CharField(max_length=30, choices=ExpenseType.choices,
                                    default=ExpenseType.GENERAL, verbose_name="نوع المصروف")
    amount       = models.DecimalField(max_digits=12, decimal_places=2,
                                       validators=[MinValueValidator(0)],
                                       verbose_name="المبلغ")
    recipient    = models.CharField(max_length=100, blank=True, null=True,
                                    verbose_name="المستلم (موظف أو جهة)")
    date         = models.DateField(default=timezone.now, verbose_name="تاريخ الصرف")
    description  = models.TextField(verbose_name="تفاصيل البيان")
    # ربط المصروف بقسم أو تخصص لأغراض التقارير والجرد
    section      = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name="expenses", verbose_name="القسم المرتبط")
    approved_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name="approved_expenses", verbose_name="اعتمد بواسطة")

    class Meta:
        verbose_name        = "مصروف تشغيلي"
        verbose_name_plural = "المصروفات التشغيلية"
        ordering            = ['-date']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['expense_type']),
            models.Index(fields=['section']),
        ]

    def __str__(self):
        return f"{self.get_expense_type_display()} — {self.amount:,.0f} ({self.date})"


# ============================================================
#  النتائج الأكاديمية
# ============================================================

class Result(models.Model):
    """جدول النتائج والدرجات الأكاديمية — التقسيم الرباعي الكامل"""
    result_no        = models.AutoField(primary_key=True, verbose_name="رقم النتيجة")
    student          = models.ForeignKey(StudentProfile, on_delete=models.CASCADE,
                                         related_name="results", verbose_name="الطالب")
    subject          = models.ForeignKey(Subject, on_delete=models.CASCADE,
                                         related_name="results", verbose_name="المقرر")
    # التقسيم الرباعي للدرجات حسب لائحة المعهد
    attendance_grade = models.DecimalField(max_digits=5, decimal_places=2, default=0.0,
                                           validators=[MinValueValidator(0), MaxValueValidator(10)],
                                           verbose_name="درجة الحضور (10)")
    activity_grade   = models.DecimalField(max_digits=5, decimal_places=2, default=0.0,
                                           validators=[MinValueValidator(0), MaxValueValidator(10)],
                                           verbose_name="درجة الأنشطة (10)")
    midterm_grade    = models.DecimalField(max_digits=5, decimal_places=2, default=0.0,
                                           validators=[MinValueValidator(0), MaxValueValidator(20)],
                                           verbose_name="درجة النصفي (20)")
    final_grade      = models.DecimalField(max_digits=5, decimal_places=2, default=0.0,
                                           validators=[MinValueValidator(0), MaxValueValidator(60)],
                                           verbose_name="درجة النهائي (60)")
    grade            = models.DecimalField(max_digits=5, decimal_places=2, default=0.0,
                                           verbose_name="الدرجة الكلية (100)")
    edit_reason      = models.TextField(blank=True, null=True, verbose_name="سبب تعديل الدرجة")
    semester         = models.ForeignKey(Semester, on_delete=models.CASCADE,
                                         related_name="results", verbose_name="الترم")
    specialty        = models.ForeignKey(Specialty, on_delete=models.CASCADE,
                                         related_name="results", verbose_name="التخصص")
    level            = models.ForeignKey(SLevel, on_delete=models.CASCADE,
                                         related_name="results", verbose_name="المستوى")
    section          = models.ForeignKey(Section, on_delete=models.CASCADE,
                                         related_name="results", verbose_name="القسم")

    class Meta:
        verbose_name        = "نتيجة طالب"
        verbose_name_plural = "النتائج الدراسية"
        unique_together     = ('student', 'subject', 'semester')
        indexes = [
            models.Index(fields=['student']),
            models.Index(fields=['semester', 'specialty']),
            models.Index(fields=['grade']),
        ]

    def save(self, *args, **kwargs):
        # حساب الدرجة الكلية تلقائياً
        self.grade = (
            self.attendance_grade +
            self.activity_grade +
            self.midterm_grade +
            self.final_grade
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.full_name} — {self.subject.sub_name}: {self.grade}"

    @property
    def letter_grade(self):
        """التقدير الحرفي للدرجة"""
        g = float(self.grade)
        if g >= 90: return 'ممتاز'
        if g >= 80: return 'جيد جداً'
        if g >= 70: return 'جيد'
        if g >= 60: return 'مقبول'
        if g >= 50: return 'ضعيف'
        return 'راسب'

    @property
    def is_passed(self):
        return self.grade >= 50

    def calculate_attendance_grade_auto(self):
        """
        احتساب درجة الحضور تلقائياً من سجل StudentAttendance.
        درجة الحضور = (نسبة الحضور / 100) × 10
        """
        qs     = StudentAttendance.objects.filter(student=self.student, subject=self.subject)
        total  = qs.count()
        if total == 0:
            return 0.0
        present = qs.filter(status=AttendanceStatus.PRESENT).count()
        return round((present / total) * 10, 2)


# ============================================================
#  الأرشفة الإلكترونية وسجل التدقيق
# ============================================================

class Document(models.Model):
    """جدول الأرشيف الإلكتروني — EDMS"""
    doc_no      = models.AutoField(primary_key=True, verbose_name="رقم الوثيقة")
    title       = models.CharField(max_length=150, verbose_name="عنوان الوثيقة")
    file        = models.FileField(upload_to='archive/%Y/%m/', verbose_name="الملف")
    doc_type    = models.CharField(max_length=30, choices=DocumentType.choices,
                                   default=DocumentType.OTHER, verbose_name="نوع الوثيقة")
    keywords    = models.CharField(max_length=200, blank=True, null=True,
                                   verbose_name="كلمات مفتاحية للبحث")
    student     = models.ForeignKey(StudentProfile, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name="documents",
                                    verbose_name="الطالب المرتبط")
    employee    = models.ForeignKey(EmployeeProfile, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name="documents",
                                    verbose_name="الموظف المرتبط")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name="uploaded_documents", verbose_name="رُفع بواسطة")
    created_at  = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الرفع")
    is_archived = models.BooleanField(default=False, verbose_name="مؤرشف رسمياً")

    class Meta:
        verbose_name        = "وثيقة"
        verbose_name_plural = "أرشيف الوثائق"
        ordering            = ['-created_at']
        indexes = [
            models.Index(fields=['doc_type']),
            models.Index(fields=['student']),
            models.Index(fields=['employee']),
        ]

    def __str__(self):
        return f"{self.title} [{self.get_doc_type_display()}]"


class AuditTrail(models.Model):
    """سجل التدقيق والتتبع الأمني لكل العمليات"""
    log_no     = models.AutoField(primary_key=True, verbose_name="رقم السجل")
    user       = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name="audit_logs", verbose_name="المستخدم")
    action     = models.CharField(max_length=20, choices=AuditAction.choices,
                                  verbose_name="الإجراء")
    model_name = models.CharField(max_length=50, verbose_name="الجدول / النموذج")
    object_id  = models.IntegerField(verbose_name="رقم السجل المعدَّل")
    timestamp  = models.DateTimeField(auto_now_add=True, verbose_name="التاريخ والوقت")
    details    = models.TextField(blank=True, null=True, verbose_name="تفاصيل التغيير")
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="عنوان IP")

    class Meta:
        verbose_name        = "سجل تدقيق"
        verbose_name_plural = "سجلات التدقيق والتتبع"
        ordering            = ['-timestamp']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['model_name']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        username = self.user.username if self.user else 'غير معروف'
        return f"{username} — {self.get_action_display()} [{self.model_name}] ({self.timestamp:%Y-%m-%d %H:%M})"


# ============================================================
#  نظام الرسائل الداخلية
# ============================================================

class Message(models.Model):
    """نموذج الرسائل الداخلية بين المستخدمين"""
    sender     = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='sent_messages', verbose_name="المرسِل")
    receiver   = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='received_messages', verbose_name="المستلِم")
    subject    = models.CharField(max_length=255, verbose_name="الموضوع")
    body       = models.TextField(verbose_name="نص الرسالة")
    is_read    = models.BooleanField(default=False, verbose_name="مقروءة؟")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="وقت الإرسال")
    is_deleted_by_sender   = models.BooleanField(default=False, verbose_name="محذوفة من المرسِل")
    is_deleted_by_receiver = models.BooleanField(default=False, verbose_name="محذوفة من المستلِم")

    class Meta:
        verbose_name        = 'رسالة'
        verbose_name_plural = 'الرسائل الداخلية'
        ordering            = ['-created_at']
        indexes = [
            models.Index(fields=['receiver', 'is_read']),
        ]

    def __str__(self):
        return f"من {self.sender.full_name} إلى {self.receiver.full_name}: {self.subject}"


# ============================================================
#  السنة الأكاديمية
# ============================================================

class AcademicYear(models.Model):
    """جدول السنة الأكاديمية"""
    year_no    = models.AutoField(primary_key=True, verbose_name="رقم السنة")
    name       = models.CharField(max_length=50, unique=True, verbose_name="اسم السنة الأكاديمية",
                                  help_text="مثال: 2025-2026")
    start_date = models.DateField(verbose_name="تاريخ البداية")
    end_date   = models.DateField(verbose_name="تاريخ النهاية")
    is_current = models.BooleanField(default=False, verbose_name="السنة الحالية؟")

    class Meta:
        verbose_name        = "سنة أكاديمية"
        verbose_name_plural = "السنوات الأكاديمية"
        ordering            = ['-start_date']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # ضمان وجود سنة حالية واحدة فقط
        if self.is_current:
            AcademicYear.objects.filter(is_current=True).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date


# ============================================================
#  مراكز التكلفة
# ============================================================

class CostCenter(models.Model):
    """
    مراكز التكلفة — ربط المصروفات بالطوابق.
    الطابق الأول: إيجار من إيرادات الأقسام الإدارية.
    الطابق الثاني: إيجار من إيرادات الأقسام الطبية.
    """
    center_no    = models.AutoField(primary_key=True, verbose_name="رقم المركز")
    name         = models.CharField(max_length=100, verbose_name="اسم مركز التكلفة")
    center_type  = models.CharField(
        max_length=20, choices=CostCenterType.choices,
        default=CostCenterType.GENERAL, verbose_name="نوع المركز"
    )
    monthly_rent = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="الإيجار الشهري",
        help_text="مبلغ الإيجار الشهري لهذا الطابق/المركز"
    )
    description  = models.TextField(blank=True, null=True, verbose_name="وصف")
    is_active    = models.BooleanField(default=True, verbose_name="نشط؟")

    class Meta:
        verbose_name        = "مركز تكلفة"
        verbose_name_plural = "مراكز التكلفة"

    def __str__(self):
        return f"{self.name} ({self.get_center_type_display()})"

    def get_total_expenses(self, month=None, year=None):
        """إجمالي المصروفات المرتبطة بهذا المركز"""
        qs = Expense.objects.all()
        if self.center_type == CostCenterType.FLOOR1_ADMIN:
            qs = qs.filter(expense_type=ExpenseType.RENT_FLOOR1)
        elif self.center_type == CostCenterType.FLOOR2_MEDICAL:
            qs = qs.filter(expense_type=ExpenseType.RENT_FLOOR2)
        if month and year:
            qs = qs.filter(date__month=month, date__year=year)
        return qs.aggregate(total=Sum('amount'))['total'] or 0

    def get_related_revenue(self):
        """إجمالي الإيرادات من الأقسام المرتبطة بهذا المركز"""
        if self.center_type == CostCenterType.FLOOR1_ADMIN:
            # إيرادات الأقسام الإدارية (سنتان)
            admin_sections = Section.objects.filter(sec_name__icontains='إدار')
            return Fee.objects.filter(
                specialty__section__in=admin_sections
            ).aggregate(total=Sum('paid'))['total'] or 0
        elif self.center_type == CostCenterType.FLOOR2_MEDICAL:
            # إيرادات الأقسام الطبية (3 سنوات)
            medical_sections = Section.objects.filter(sec_name__icontains='طب')
            return Fee.objects.filter(
                specialty__section__in=medical_sections
            ).aggregate(total=Sum('paid'))['total'] or 0
        return 0


# ============================================================
#  سجل محاضرات المدرسين (تتبع ساعات التدريس)
# ============================================================

class TeacherDailyLog(models.Model):
    """
    سجل يومي لمحاضرات المدرسين — لاحتساب الأجور بالساعة.
    يُستخدم لكل من:
    - المدرسين المتعاقدين بالساعة (TeacherProfile)
    - الموظفين الإداريين الذين يدرسون بعقد مختلط (EmployeeProfile)
    """
    log_no       = models.AutoField(primary_key=True, verbose_name="رقم السجل")
    teacher      = models.ForeignKey(
        TeacherProfile, on_delete=models.CASCADE, null=True, blank=True,
        related_name="lecture_logs", verbose_name="المدرس"
    )
    employee     = models.ForeignKey(
        EmployeeProfile, on_delete=models.CASCADE, null=True, blank=True,
        related_name="lecture_logs", verbose_name="الموظف المدرس"
    )
    subject      = models.ForeignKey(
        Subject, on_delete=models.CASCADE,
        related_name="lecture_logs", verbose_name="المقرر"
    )
    date         = models.DateField(default=timezone.now, verbose_name="التاريخ")
    hours_taught = models.DecimalField(
        max_digits=4, decimal_places=1, default=1,
        validators=[MinValueValidator(0.5), MaxValueValidator(10)],
        verbose_name="عدد الساعات"
    )
    notes        = models.CharField(max_length=200, blank=True, null=True, verbose_name="ملاحظات")

    class Meta:
        verbose_name        = "سجل محاضرة"
        verbose_name_plural = "سجلات المحاضرات"
        ordering            = ['-date']
        indexes = [
            models.Index(fields=['teacher', 'date']),
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        who = self.teacher.full_name if self.teacher else (self.employee.full_name if self.employee else "—")
        return f"{who} — {self.subject.sub_name} ({self.date}) [{self.hours_taught}h]"

    def clean(self):
        """التأكد من أن السجل مرتبط بمدرس أو موظف واحد على الأقل"""
        from django.core.exceptions import ValidationError
        if not self.teacher and not self.employee:
            raise ValidationError("يجب تحديد مدرس أو موظف للسجل.")
        if self.teacher and self.employee:
            raise ValidationError("لا يمكن ربط السجل بمدرس وموظف معاً.")


# ============================================================
#  طلبات الإجازة
# ============================================================

class LeaveRequest(models.Model):
    """نظام طلبات الإجازة للموظفين والمدرسين"""
    request_no   = models.AutoField(primary_key=True, verbose_name="رقم الطلب")
    requester    = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="leave_requests", verbose_name="مقدم الطلب"
    )
    leave_type   = models.CharField(max_length=50, verbose_name="نوع الإجازة",
                                    help_text="مثال: سنوية، مرضية، طارئة")
    start_date   = models.DateField(verbose_name="تاريخ بداية الإجازة")
    end_date     = models.DateField(verbose_name="تاريخ نهاية الإجازة")
    reason       = models.TextField(verbose_name="سبب الإجازة")
    status       = models.CharField(
        max_length=20, choices=LeaveStatus.choices,
        default=LeaveStatus.PENDING, verbose_name="حالة الطلب"
    )
    reviewed_by  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_leaves", verbose_name="تمت المراجعة بواسطة"
    )
    review_notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات المراجع")
    created_at   = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ تقديم الطلب")
    updated_at   = models.DateTimeField(auto_now=True, verbose_name="آخر تحديث")

    class Meta:
        verbose_name        = "طلب إجازة"
        verbose_name_plural = "طلبات الإجازة"
        ordering            = ['-created_at']
        indexes = [
            models.Index(fields=['requester']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"طلب إجازة {self.requester.full_name} ({self.get_status_display()})"

    @property
    def duration_days(self):
        """عدد أيام الإجازة"""
        return (self.end_date - self.start_date).days + 1


# ============================================================
#  نظام الإشعارات والتعميمات
# ============================================================

class Notification(models.Model):
    """نظام الإشعارات والتنبيهات والتعميمات الداخلية"""
    notif_no        = models.AutoField(primary_key=True, verbose_name="رقم الإشعار")
    title           = models.CharField(max_length=255, verbose_name="عنوان الإشعار")
    body            = models.TextField(verbose_name="نص الإشعار")
    notif_type      = models.CharField(
        max_length=20, choices=NotificationType.choices,
        default=NotificationType.INFO, verbose_name="نوع الإشعار"
    )
    sender          = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name="sent_notifications", verbose_name="المرسِل"
    )
    # المستلم الفردي (اختياري — إذا فارغ فهو تعميم عام)
    recipient       = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True,
        related_name="notifications", verbose_name="المستلِم"
    )
    # التعميم لدور معين (اختياري)
    target_role     = models.CharField(
        max_length=20, choices=RoleChoices.choices,
        blank=True, null=True, verbose_name="الدور المستهدف",
        help_text="لإرسال تعميم لكل أصحاب هذا الدور (اتركه فارغاً للتعميم العام)"
    )
    is_read         = models.BooleanField(default=False, verbose_name="مقروء؟")
    is_broadcast    = models.BooleanField(default=False, verbose_name="تعميم عام؟")
    created_at      = models.DateTimeField(auto_now_add=True, verbose_name="وقت الإرسال")

    class Meta:
        verbose_name        = "إشعار"
        verbose_name_plural = "الإشعارات والتعميمات"
        ordering            = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notif_type']),
            models.Index(fields=['target_role']),
        ]

    def __str__(self):
        target = self.recipient.full_name if self.recipient else "تعميم عام"
        return f"[{self.get_notif_type_display()}] {self.title} → {target}"


# ============================================================
#  سجل الرواتب الشهري (Payroll Record)
# ============================================================

class PayrollRecord(models.Model):
    """
    سجل كشف الراتب الشهري — يُنشأ بواسطة محرك الرواتب (Payroll Engine).
    يجمع: الراتب الأساسي + أجر ساعات التدريس − خصومات الغياب − ضرائب.
    """
    payroll_no       = models.AutoField(primary_key=True, verbose_name="رقم كشف الراتب")
    # ربط بالموظف أو المدرس
    employee         = models.ForeignKey(
        EmployeeProfile, on_delete=models.CASCADE, null=True, blank=True,
        related_name="payroll_records", verbose_name="الموظف"
    )
    teacher          = models.ForeignKey(
        TeacherProfile, on_delete=models.CASCADE, null=True, blank=True,
        related_name="payroll_records", verbose_name="المدرس"
    )
    # فترة الكشف
    month            = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name="الشهر"
    )
    year             = models.PositiveIntegerField(verbose_name="السنة")
    # مكونات الراتب
    basic_salary     = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                           verbose_name="الراتب الأساسي")
    teaching_hours   = models.DecimalField(max_digits=6, decimal_places=1, default=0,
                                           verbose_name="ساعات التدريس")
    hourly_rate      = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                           verbose_name="أجر الساعة")
    teaching_pay     = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                           verbose_name="مستحقات التدريس")
    bonuses          = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                           verbose_name="مكافآت وحوافز")
    absence_days     = models.PositiveIntegerField(default=0, verbose_name="أيام الغياب")
    absence_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                            verbose_name="خصم الغياب")
    other_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                           verbose_name="خصومات أخرى (ضرائب، إلخ)")
    net_salary       = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                           verbose_name="صافي الراتب")
    is_paid          = models.BooleanField(default=False, verbose_name="تم الصرف؟")
    paid_date        = models.DateField(blank=True, null=True, verbose_name="تاريخ الصرف")
    notes            = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    created_at       = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")

    class Meta:
        verbose_name        = "كشف راتب شهري"
        verbose_name_plural = "كشوفات الرواتب الشهرية"
        ordering            = ['-year', '-month']
        indexes = [
            models.Index(fields=['month', 'year']),
            models.Index(fields=['is_paid']),
        ]
        
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.employee:
            if PayrollRecord.objects.filter(employee=self.employee, month=self.month, year=self.year).exclude(pk=self.pk).exists():
                raise ValidationError("يوجد كشف راتب لهذا الموظف في هذا الشهر بالفعل.")
        if self.teacher:
            if PayrollRecord.objects.filter(teacher=self.teacher, month=self.month, year=self.year).exclude(pk=self.pk).exists():
                raise ValidationError("يوجد كشف راتب لهذا المدرس في هذا الشهر بالفعل.")

    def save(self, *args, **kwargs):
        """حساب صافي الراتب تلقائياً"""
        self.teaching_pay = self.teaching_hours * self.hourly_rate
        self.net_salary = (
            self.basic_salary
            + self.teaching_pay
            + self.bonuses
            - self.absence_deduction
            - self.other_deductions
        )
        super().save(*args, **kwargs)

    def __str__(self):
        who = "—"
        if self.employee:
            who = self.employee.full_name
        elif self.teacher:
            who = self.teacher.full_name
        return f"كشف راتب {who} — {self.month}/{self.year} — صافي: {self.net_salary:,.0f}"

    @property
    def period_display(self):
        """عرض الفترة كنص"""
        months = ['', 'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
                  'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']
        return f"{months[self.month]} {self.year}"


# ============================================================
#  مهام الموظفين (Employee Tasks)
# ============================================================

class EmployeeTask(models.Model):
    """جدول مهام الموظفين الإداريين"""
    task_no = models.AutoField(primary_key=True, verbose_name="رقم المهمة")
    employee = models.ForeignKey(
        EmployeeProfile, on_delete=models.CASCADE,
        related_name='tasks', verbose_name="الموظف"
    )
    title = models.CharField(max_length=200, verbose_name="عنوان المهمة")
    description = models.TextField(verbose_name="وصف المهمة")
    assigned_date = models.DateField(default=timezone.now, verbose_name="تاريخ التكليف")
    due_date = models.DateField(blank=True, null=True, verbose_name="تاريخ التسليم المتوقع")
    
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('in_progress', 'قيد التنفيذ'),
        ('completed', 'مكتملة'),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='pending', verbose_name="الحالة"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")

    class Meta:
        verbose_name = "مهمة موظف"
        verbose_name_plural = "مهام الموظفين"
        ordering = ['-assigned_date', '-created_at']
        indexes = [
            models.Index(fields=['employee', 'status']),
        ]

    def __str__(self):
        return f"{self.title} — {self.employee.full_name} ({self.get_status_display()})"

# ============================================================
#  نماذج الكنترول (Control Module)
# ============================================================

class ExamSchedule(models.Model):
    """جدول الامتحانات"""
    schedule_no = models.AutoField(primary_key=True, verbose_name="رقم الجدول")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='exam_schedules', verbose_name="المقرر")
    exam_date = models.DateField(verbose_name="تاريخ الامتحان")
    start_time = models.TimeField(verbose_name="وقت البدء")
    end_time = models.TimeField(verbose_name="وقت الانتهاء")
    hall_name = models.CharField(max_length=100, verbose_name="القاعة")
    supervisor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='supervised_exams', verbose_name="المراقب")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'جدول امتحان'
        verbose_name_plural = 'جداول الامتحانات'
        ordering = ['-exam_date', 'start_time']

    def __str__(self):
        return f"امتحان {self.subject.sub_name} - {self.exam_date}"

class ExamPaperTracking(models.Model):
    """تتبع حركة أوراق الامتحانات ودفاتر الإجابة"""
    schedule = models.OneToOneField(ExamSchedule, on_delete=models.CASCADE, related_name='tracking', verbose_name="الامتحان")
    
    # مرحلة ما قبل الامتحان
    questions_submitted = models.BooleanField(default=False, verbose_name="تم تسليم الأسئلة من الأستاذ")
    papers_printed = models.BooleanField(default=False, verbose_name="تم تصوير أوراق الأسئلة")
    
    # يوم الامتحان
    delivered_to_hall = models.BooleanField(default=False, verbose_name="تم تسليم الأوراق للقاعة")
    returned_from_hall = models.BooleanField(default=False, verbose_name="تم استرجاع دفاتر الإجابة")
    
    # مرحلة التصحيح والنتائج
    delivered_to_teacher = models.BooleanField(default=False, verbose_name="تم تسليم الدفاتر للأستاذ للتصحيح")
    returned_graded = models.BooleanField(default=False, verbose_name="تم استرجاع الدفاتر مصححة")
    results_approved = models.BooleanField(default=False, verbose_name="تم اعتماد النتائج")
    
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات الكنترول")

    class Meta:
        verbose_name = 'تتبع أوراق الامتحان'
        verbose_name_plural = 'تتبع أوراق الامتحانات'

    def __str__(self):
        return f"تتبع: {self.schedule.subject.sub_name}"
