from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count, Sum
from django.utils import timezone
from .models import (
    User, SLevel, Section, Specialty, Administration,
    EmployeeProfile, TeacherProfile, StudentProfile, Parent,
    Subject, StudentAttendance, EmployeeDailyLog, Salary,
    Penalty, Fee, FeeDetail, Semester, Result, Message,
    Expense, FeePayment, Document, AuditTrail, LeaveRequest,
    Notification, PayrollRecord, CostCenter, AcademicYear,
    TeacherDailyLog, EmployeeTask,
    RoleChoices, StatusChoices, ExpenseType, DocumentType, AuditAction,
    ContractType, LeaveStatus, NotificationType, AttendanceStatus
)

from .services.user_services import get_or_create_profile, create_system_user, update_system_user
from .services.academic_services import register_student_to_course, drop_student_course, update_student_grades
from .services.finance_services import create_student_fee, process_fee_payment, record_expense
from .services.document_services import upload_and_archive_document, delete_archived_document
from .services.hr_services import (
    record_employee_attendance, get_employee_financials, submit_hr_request,
    submit_leave_request, review_leave_request, get_pending_leave_requests,
    generate_payroll, get_payroll_summary, mark_payroll_as_paid
)
from .services.notification_services import (
    send_notification, send_role_broadcast, send_broadcast,
    get_user_notifications, mark_as_read, mark_all_as_read, get_unread_count
)

def login_view(request):
    """صفحة تسجيل الدخول"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        
        if not username or not password:
            messages.error(request, 'يرجى تعبئة جميع الحقول')
            return redirect('login')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            # إنشاء الملف التعريفي تلقائياً عند تسجيل الدخول لأول مرة
            get_or_create_profile(user)
            return redirect('dashboard')
        else:
            messages.error(request, 'بيانات الدخول غير صحيحة')
    
    return render(request, 'institute/login.html')


def logout_view(request):
    """تسجيل الخروج"""
    logout(request)
    return redirect('login')


@login_required(login_url='login')
def dashboard_view(request):
    """لوحة التحكم الرئيسية حسب دور المستخدم"""
    user = request.user
    context = {'user': user}
    
    # حساب الإشعارات غير المقروءة
    context['unread_notifs'] = get_unread_count(user)
    
    # التأكد من وجود ملف تعريفي للمستخدم الحالي
    profile = get_or_create_profile(user)
    
    if user.role == 'manager':
        return redirect('manager_dashboard')
    
    elif user.role == 'admin':
        context['total_users'] = User.objects.count()
        
        # تحويل أدوار المستخدمين للعربية
        from django.db.models import Count
        roles_qs = User.objects.values('role').annotate(count=Count('id'))
        roles_dict = {}
        for r in roles_qs:
            role_val = r['role']
            role_label = dict(RoleChoices.choices).get(role_val, role_val)
            roles_dict[role_label] = r['count']
            
        context['users_by_role'] = roles_dict
        context['total_invoices'] = Fee.objects.count()
        context['paid_invoices'] = Fee.objects.filter(remaining=0).count()
        template = 'institute/dashboards/admin_dashboard.html'
    
    elif user.role == 'faculty':
        context['courses'] = Subject.objects.filter(teacher=profile)
        context['total_students'] = Result.objects.filter(subject__teacher=profile).values('student').distinct().count()
        template = 'institute/dashboards/faculty_dashboard.html'
    
    elif user.role == 'student':
        context['profile'] = profile
        context['enrollments'] = Result.objects.filter(student=profile)
        context['total_credits'] = Result.objects.filter(student=profile).aggregate(Sum('subject__hours'))['subject__hours__sum'] or 0
        context['invoices'] = Fee.objects.filter(student=profile)
        context['unpaid_amount'] = Fee.objects.filter(student=profile).aggregate(Sum('remaining'))['remaining__sum'] or 0
        template = 'institute/dashboards/student_dashboard.html'
    
    elif user.role == 'admission':
        context['total_students'] = StudentProfile.objects.count()
        context['recent_students'] = StudentProfile.objects.order_by('-id')[:10]
        template = 'institute/dashboards/admission_dashboard.html'
    
    elif user.role == 'finance':
        context['total_invoices'] = Fee.objects.count()
        context['paid_invoices'] = Fee.objects.filter(remaining=0).count()
        context['unpaid_invoices'] = Fee.objects.filter(remaining__gt=0).count()
        context['total_revenue'] = Fee.objects.aggregate(Sum('paid'))['paid__sum'] or 0
        template = 'institute/dashboards/finance_dashboard.html'
    
    elif user.role in ['staff', 'hr']:
        return redirect('employee_portal')
        
    elif user.role == 'dept_head':
        return redirect('dept_head_dashboard')
        
    elif user.role == 'control':
        return redirect('control_dashboard')

    else:
        template = 'institute/dashboards/default_dashboard.html'
    
    return render(request, template, context)


# ============= وظائف بوابة الموظف (Employee Portal) =============

@login_required(login_url='login')
def employee_portal_view(request):
    """بوابة الموظف الشاملة لأي موظف (إداري، مدرس، شؤون، إلخ)"""
    user = request.user
    
    # التأكد من أن المستخدم موظف (وليس طالب)
    if user.role == 'student':
        messages.error(request, 'ليس لديك صلاحية للوصول إلى بوابة الموظف')
        return redirect('dashboard')
        
    profile = None
    if hasattr(user, 'employee_profile'):
        profile = user.employee_profile
    elif hasattr(user, 'teacher_profile'):
        profile = user.teacher_profile
        
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # تسجيل حضور/انصراف
        if action in ['check_in', 'check_out']:
            if hasattr(user, 'employee_profile'):
                success, msg = record_employee_attendance(user, action)
                if success:
                    messages.success(request, msg)
                else:
                    messages.error(request, msg)
            else:
                messages.warning(request, 'نظام البصمة متاح للإداريين فقط حالياً')
            return redirect('employee_portal')
            
        # رفع طلب للـ HR
        elif action == 'submit_request':
            req_type = request.POST.get('request_type', 'طلب عام')
            content = request.POST.get('content', '')
            try:
                submit_hr_request(user, req_type, content)
                messages.success(request, 'تم إرسال طلبك بنجاح إلى الإدارة.')
            except ValueError as e:
                messages.error(request, str(e))
            return redirect('employee_portal')
            
        # طلب إجازة جديد
        elif action == 'submit_leave':
            leave_type = request.POST.get('leave_type')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            reason = request.POST.get('reason')
            try:
                submit_leave_request(user, leave_type, start_date, end_date, reason)
                messages.success(request, 'تم رفع طلب الإجازة بنجاح، بانتظار المراجعة.')
            except Exception as e:
                messages.error(request, str(e))
            return redirect('employee_portal')

        # تحديث حالة المهمة
        elif action == 'update_task_status':
            task_id = request.POST.get('task_id')
            new_status = request.POST.get('new_status')
            if hasattr(user, 'employee_profile') and task_id and new_status:
                try:
                    task = EmployeeTask.objects.get(task_no=task_id, employee=user.employee_profile)
                    task.status = new_status
                    task.save()
                    messages.success(request, 'تم تحديث حالة المهمة بنجاح.')
                except EmployeeTask.DoesNotExist:
                    messages.error(request, 'عفواً، المهمة غير موجودة.')
            return redirect('employee_portal')

    # جلب بيانات الحضور اليوم
    today_log = None
    if hasattr(user, 'employee_profile'):
        today_log = EmployeeDailyLog.objects.filter(employee=user.employee_profile, date=timezone.now().date()).first()
        
    financials = get_employee_financials(user)
    
    # جلب الرسائل الأخيرة (التي قد تحتوي على ردود الإدارة)
    recent_messages = Message.objects.filter(receiver=user).order_by('-created_at')[:5]
    
    # جلب المهام
    tasks = []
    if hasattr(user, 'employee_profile'):
        tasks = user.employee_profile.tasks.all()

    # جلب جميع سجلات الحضور السابقة
    all_logs = []
    if hasattr(user, 'employee_profile'):
        all_logs = user.employee_profile.daily_logs.order_by('-date')[:30] # آخر 30 يوم
        
    # جلب كشوف الرواتب
    payroll_history = []
    if hasattr(user, 'employee_profile'):
        payroll_history = user.employee_profile.payroll_records.order_by('-year', '-month')
    elif hasattr(user, 'teacher_profile'):
        payroll_history = user.teacher_profile.payroll_records.order_by('-year', '-month')

    context = {
        'profile': profile,
        'today_log': today_log,
        'financials': financials,
        'recent_messages': recent_messages,
        'leave_requests': LeaveRequest.objects.filter(requester=user).order_by('-created_at')[:10],
        'recent_notifs': get_user_notifications(user, limit=5),
        'tasks': tasks,
        'all_logs': all_logs,
        'payroll_history': payroll_history,
    }
    return render(request, 'institute/dashboards/employee_portal.html', context)


# ============= وظائف الموارد البشرية (HR) =============

@login_required(login_url='login')
def hr_dashboard_view(request):
    """لوحة تحكم مدير الموارد البشرية"""
    if request.user.role not in ['hr', 'manager']:
        messages.error(request, 'ليس لديك صلاحية للوصول إلى هذه الصفحة')
        return redirect('dashboard')
        
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_employee':
            try:
                # إنشاء User
                username = request.POST.get('username')
                full_name = request.POST.get('full_name')
                email = request.POST.get('email', '')
                password = request.POST.get('password')
                
                if User.objects.filter(username=username).exists():
                    messages.error(request, 'اسم المستخدم موجود مسبقاً.')
                else:
                    new_user = User.objects.create_user(
                        username=username,
                        password=password,
                        first_name=full_name.split()[0] if full_name else '',
                        last_name=' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else '',
                        email=email,
                        role='staff'
                    )
                    
                    profile = EmployeeProfile(user=new_user)
                    
                    profile.job_title = request.POST.get('job_title', '')
                    admin_id = request.POST.get('administration')
                    if admin_id:
                        profile.administration_id = admin_id
                    profile.national_id = request.POST.get('national_id', '')
                    profile.gender = request.POST.get('gender', 'ذكر')
                    profile.contract_type = request.POST.get('contract_type', 'دائم')
                    profile.basic_salary_amount = request.POST.get('basic_salary_amount') or 0
                    profile.hourly_rate = request.POST.get('hourly_rate') or 0
                    
                    from django.utils import timezone
                    hire_date = request.POST.get('hire_date')
                    if hire_date:
                        profile.hire_date = hire_date
                    else:
                        profile.hire_date = timezone.now().date()
                        
                    profile.save()
                    messages.success(request, f'تم إضافة الموظف {full_name} بنجاح.')
            except Exception as e:
                messages.error(request, f'حدث خطأ: {e}')
                
        elif action == 'edit_employee':
            emp_id = request.POST.get('emp_id')
            try:
                profile = EmployeeProfile.objects.get(id=emp_id)
                user = profile.user
                
                # تحديث User
                full_name = request.POST.get('full_name')
                if full_name:
                    user.first_name = full_name.split()[0]
                    user.last_name = ' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else ''
                user.email = request.POST.get('email', user.email)
                
                password = request.POST.get('password')
                if password:
                    user.set_password(password)
                user.save()
                
                # تحديث Profile
                profile.job_title = request.POST.get('job_title', profile.job_title)
                admin_id = request.POST.get('administration')
                if admin_id:
                    profile.administration_id = admin_id
                profile.national_id = request.POST.get('national_id', profile.national_id)
                profile.gender = request.POST.get('gender', profile.gender)
                profile.contract_type = request.POST.get('contract_type', profile.contract_type)
                profile.basic_salary_amount = request.POST.get('basic_salary_amount') or profile.basic_salary_amount
                profile.hourly_rate = request.POST.get('hourly_rate') or profile.hourly_rate
                
                hire_date = request.POST.get('hire_date')
                if hire_date:
                    profile.hire_date = hire_date
                    
                profile.save()
                messages.success(request, 'تم تحديث بيانات الموظف بنجاح.')
            except EmployeeProfile.DoesNotExist:
                messages.error(request, 'الموظف غير موجود.')
            except Exception as e:
                messages.error(request, f'حدث خطأ: {e}')
                
        elif action == 'delete_employee':
            emp_id = request.POST.get('emp_id')
            try:
                profile = EmployeeProfile.objects.get(id=emp_id)
                profile.status = StatusChoices.INACTIVE  # موقوف / مفصول
                profile.save()
                
                user = profile.user
                user.is_active = False  # تعطيل حساب الدخول
                user.save()
                
                messages.success(request, f'تم إيقاف الموظف {user.get_full_name()} بنجاح.')
            except EmployeeProfile.DoesNotExist:
                messages.error(request, 'الموظف غير موجود.')
                
        return redirect('hr_dashboard')

    today = timezone.now().date()
    
    # إحصائيات عامة (للموظفين النشطين أو في إجازة فقط)
    total_employees = EmployeeProfile.objects.filter(status__in=[StatusChoices.ACTIVE, StatusChoices.ON_LEAVE]).count()
    present_today = EmployeeDailyLog.objects.filter(date=today, status=AttendanceStatus.PRESENT).count()
    on_leave = EmployeeProfile.objects.filter(status=StatusChoices.ON_LEAVE).count()
    
    # يوميات الحضور لليوم
    todays_attendance = EmployeeDailyLog.objects.filter(date=today).select_related('employee__user')
    
    # الموظفون الإداريون
    employees = EmployeeProfile.objects.all().select_related('user', 'administration').order_by('-id')
    
    search_query = request.GET.get('search_query', '')
    if search_query:
        employees = employees.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(national_id__icontains=search_query) |
            Q(user__phone__icontains=search_query)
        )
        
    administrations = Administration.objects.all()
    contract_types = ContractType.choices
    
    context = {
        'total_employees': total_employees,
        'present_today': present_today,
        'on_leave': on_leave,
        'todays_attendance': todays_attendance,
        'employees': employees,
        'search_query': search_query,
        'administrations': administrations,
        'contract_types': contract_types,
        'pending_leaves_count': get_pending_leave_requests().count()
    }
    return render(request, 'institute/dashboards/hr_dashboard.html', context)


@login_required(login_url='login')
def hr_leave_requests_view(request):
    """إدارة طلبات الإجازة (لـ HR)"""
    if request.user.role not in ['hr', 'manager']:
        return redirect('dashboard')
        
    if request.method == 'POST':
        action = request.POST.get('action')
        req_id = request.POST.get('request_id')
        notes = request.POST.get('review_notes', '')
        
        try:
            if action == 'approve':
                review_leave_request(req_id, request.user, True, notes)
                messages.success(request, 'تمت الموافقة على الإجازة.')
            elif action == 'reject':
                review_leave_request(req_id, request.user, False, notes)
                messages.success(request, 'تم رفض الإجازة.')
        except Exception as e:
            messages.error(request, str(e))
            
        return redirect('hr_leave_requests')
        
    pending = get_pending_leave_requests()
    history = LeaveRequest.objects.exclude(status=LeaveStatus.PENDING).order_by('-updated_at')[:50]
    
    context = {'pending': pending, 'history': history}
    return render(request, 'institute/dashboards/hr_leave_requests.html', context)


@login_required(login_url='login')
def hr_payroll_view(request):
    """محرك الرواتب (Payroll Engine)"""
    if request.user.role not in ['hr', 'manager', 'finance']:
        return redirect('dashboard')
        
    today = timezone.now().date()
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))
    
    if request.method == 'POST':
        action = request.POST.get('action')
        p_month = int(request.POST.get('month', month))
        p_year = int(request.POST.get('year', year))
        
        if action == 'generate':
            ptype = request.POST.get('person_type', 'employee')
            generated, errors = generate_payroll(p_month, p_year, ptype)
            if generated:
                messages.success(request, f'تم توليد {len(generated)} كشوف رواتب بنجاح.')
            if errors:
                for err in errors:
                    messages.error(request, err)
                    
        elif action == 'mark_paid':
            pid = request.POST.get('payroll_id')
            try:
                mark_payroll_as_paid(pid)
                messages.success(request, 'تم تسجيل الكشف كمدفوع.')
            except Exception as e:
                messages.error(request, str(e))
                
        return redirect(f'/hr/payroll/?month={p_month}&year={p_year}')
        
    records = PayrollRecord.objects.filter(month=month, year=year).select_related('employee__user', 'teacher__user')
    summary = get_payroll_summary(month, year)
    
    context = {
        'records': records,
        'summary': summary,
        'month': month,
        'year': year,
        'months': range(1, 13),
        'years': range(2025, 2030)
    }
    return render(request, 'institute/dashboards/hr_payroll.html', context)


@login_required(login_url='login')
def notifications_view(request):
    """عرض الإشعارات والتعميمات للمستخدم أو إرسالها (للإدارة)"""
    user = request.user
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'send' and user.role in ['manager', 'hr', 'admin']:
            title = request.POST.get('title')
            body = request.POST.get('body')
            n_type = request.POST.get('notif_type', NotificationType.INFO)
            target = request.POST.get('target', 'all')
            
            if target == 'all':
                send_broadcast(user, title, body, n_type)
            elif target.startswith('role_'):
                r = target.split('_')[1]
                send_role_broadcast(user, r, title, body, n_type)
            else:
                try:
                    recip = User.objects.get(id=int(target))
                    send_notification(user, recip, title, body, n_type)
                except:
                    pass
            messages.success(request, 'تم إرسال الإشعار بنجاح.')
            return redirect('notifications')
            
        elif action == 'mark_read':
            nid = request.POST.get('notif_id')
            mark_as_read(nid, user)
            return JsonResponse({'status': 'ok'})
            
        elif action == 'mark_all_read':
            mark_all_as_read(user)
            messages.success(request, 'تم تحديد الكل كمقروء.')
            return redirect('notifications')
            
    notifs = get_user_notifications(user, limit=50)
    
    context = {'notifications': notifs, 'notif_types': NotificationType.choices}
    if user.role in ['manager', 'hr', 'admin']:
        context['roles'] = RoleChoices.choices
        context['users'] = User.objects.filter(is_active=True).exclude(id=user.id)
        
    return render(request, 'institute/dashboards/notifications.html', context)


@login_required(login_url='login')
def dept_head_dashboard_view(request):
    """لوحة تحكم رئيس القسم الأكاديمي"""
    if request.user.role != 'dept_head':
        return redirect('dashboard')
        
    profile = get_or_create_profile(request.user)
    section = getattr(profile, 'managed_section', None)
    
    if not section:
        messages.warning(request, "لم يتم ربطك بقسم أكاديمي بعد. يرجى مراجعة الإدارة.")
        return render(request, 'institute/dashboards/dept_head_dashboard.html', {})
        
    specialties = Specialty.objects.filter(section=section)
    teachers = TeacherProfile.objects.filter(specialty__in=specialties).distinct()
    subjects = Subject.objects.filter(specialty__in=specialties)
    students = StudentProfile.objects.filter(specialty__in=specialties, status='نشط')
    
    context = {
        'section': section,
        'specialties': specialties,
        'teachers': teachers,
        'subjects': subjects,
        'total_students': students.count()
    }
    return render(request, 'institute/dashboards/dept_head_dashboard.html', context)


# ============= وظائف إدارة المستخدمين (للمدير) =============

@login_required(login_url='login')
def manager_users_view(request):
    """إدارة المستخدمين والموظفين"""
    if request.user.role not in ['manager', 'admin']:
        messages.error(request, 'ليس لديك صلاحية للوصول إلى هذه الصفحة')
        return redirect('dashboard')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            username = request.POST.get('username', '')
            full_name = request.POST.get('full_name', '')
            email = request.POST.get('email', '')
            role = request.POST.get('role', 'student')
            
            try:
                create_system_user(username, '123456', full_name, email, role)
                messages.success(request, f'تم إضافة المستخدم {username} بنجاح')
            except ValueError as e:
                messages.error(request, str(e))
            return redirect('manager_users')

        elif action == 'edit':
            user_id = request.POST.get('user_id')
            full_name = request.POST.get('full_name', '')
            email = request.POST.get('email', '')
            role = request.POST.get('role', '')
            
            user_to_edit = update_system_user(user_id, full_name, email, role)
            
            messages.success(request, f'تم تعديل بيانات المستخدم {user_to_edit.username} بنجاح')
            return redirect('manager_users')
        
        elif action == 'delete':
            user_id = request.POST.get('user_id')
            if user_id != str(request.user.id):
                user = get_object_or_404(User, id=user_id)
                user.delete()
                messages.success(request, 'تم حذف المستخدم بنجاح')
            else:
                messages.error(request, 'لا يمكنك حذف حسابك الخاص')
            return redirect('manager_users')
    
    users = User.objects.all().order_by('-date_joined')
    context = {
        'users': users,
        'role_choices': RoleChoices.choices
    }
    return render(request, 'institute/dashboards/manager_users.html', context)


@login_required(login_url='login')
def manager_departments_view(request):
    """إدارة الأقسام (تتعامل مع الأقسام العامة Section)"""
    if request.user.role not in ['manager', 'admin']:
        messages.error(request, 'ليس لديك صلاحية للوصول إلى هذه الصفحة')
        return redirect('dashboard')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            name = request.POST.get('name', '')
            code = request.POST.get('code', '')
            
            try:
                sec_no = int(code)
                if Section.objects.filter(sec_no=sec_no).exists():
                    messages.error(request, 'رقم القسم موجود بالفعل')
                else:
                    Section.objects.create(sec_no=sec_no, sec_name=name)
                    messages.success(request, f'تم إضافة القسم {name} بنجاح')
            except ValueError:
                messages.error(request, 'يجب أن يكون كود القسم رقماً صحيحاً')
                
            return redirect('manager_departments')
            
        elif action == 'edit':
            dept_id = request.POST.get('dept_id')
            name = request.POST.get('name', '')
            
            dept = get_object_or_404(Section, sec_no=dept_id)
            dept.sec_name = name
            dept.save()
            messages.success(request, f'تم تعديل بيانات القسم بنجاح')
            return redirect('manager_departments')
            
        elif action == 'delete':
            dept_id = request.POST.get('dept_id')
            dept = get_object_or_404(Section, sec_no=dept_id)
            dept.delete()
            messages.success(request, 'تم حذف القسم بنجاح')
            return redirect('manager_departments')

    departments = Section.objects.all().order_by('sec_no')
    # تهيئة البيانات لتتوافق مع تمثيل الواجهة (name, code)
    formatted_departments = []
    for d in departments:
        formatted_departments.append({
            'id': d.sec_no,
            'name': d.sec_name,
            'code': d.sec_no
        })
        
    context = {
        'departments': formatted_departments,
    }
    return render(request, 'institute/dashboards/manager_departments.html', context)


# ============= وظائف القبول والتسجيل =============

@login_required(login_url='login')
def admission_students_view(request):
    """إدارة الطلاب من قبل موظف القبول والتسجيل"""
    if request.user.role not in ['admission', 'manager']:
        messages.error(request, 'ليس لديك صلاحية للوصول إلى هذه الصفحة')
        return redirect('dashboard')
        
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            username = request.POST.get('username', '')
            full_name = request.POST.get('full_name', '')
            email = request.POST.get('email', '')
            phone = request.POST.get('phone', '')
            address = request.POST.get('address', '')
            qualification = request.POST.get('qualification', '')
            parent_name = request.POST.get('parent_name', '')
            parent_phone = request.POST.get('parent_phone', '')
            specialty_id = request.POST.get('specialty')
            level_id = request.POST.get('level')
            
            try:
                user = create_system_user(
                    username, '123456', full_name, email, 'student',
                    specialty_id=specialty_id, level_id=level_id,
                    phone=phone, address=address, qualification=qualification,
                    parent_name=parent_name, parent_phone=parent_phone
                )
                
                # رفع الوثائق إذا وجدت
                if request.FILES.get('document'):
                    doc_file = request.FILES['document']
                    from institute.services.document_services import upload_and_archive_document
                    profile = get_or_create_profile(user)
                    upload_and_archive_document(
                        title=f"وثيقة تسجيل الطالب {full_name or username}",
                        doc_type='other',
                        file=doc_file,
                        student=profile,
                        employee=None,
                        uploaded_by=request.user
                    )
                    
                messages.success(request, f'تم تسجيل الطالب {full_name or username} بنجاح')
            except ValueError as e:
                messages.error(request, str(e))
            return redirect('admission_students')
                
        elif action == 'delete':
            user_id = request.POST.get('user_id')
            user = get_object_or_404(User, id=user_id, role='student')
            user.delete()
            messages.success(request, 'تم حذف الطالب بنجاح')
            return redirect('admission_students')
            
    students = StudentProfile.objects.all().order_by('-id')
    context = {
        'students': students,
        'specialties': Specialty.objects.all(),
        'levels': SLevel.objects.all()
    }
    return render(request, 'institute/dashboards/admission_students.html', context)


# ============= وظائف الطلاب =============

@login_required(login_url='login')
def student_register_view(request):
    """تسجيل المقررات للطالب"""
    if request.user.role != 'student':
        messages.error(request, 'ليس لديك صلاحية للوصول إلى هذه الصفحة')
        return redirect('dashboard')
    
    student_profile = get_or_create_profile(request.user)
    
    # استخراج الترم الحالي
    from datetime import date
    semester, _ = Semester.objects.get_or_create(
        term_no=1,
        defaults={
            'term_name': 'الترم الأول',
            'start_date': date(2026, 1, 1),
            'end_date': date(2026, 6, 30),
            'level': student_profile.level or SLevel.objects.first() or SLevel.objects.get_or_create(lev_no=1, defaults={'lev_name': 'مستوى أول'})[0]
        }
    )
    
    if request.method == 'POST':
        action = request.POST.get('action')
        course_id = request.POST.get('course_id')
        
        if action == 'register':
            subject = get_object_or_404(Subject, sub_no=course_id)
            if Result.objects.filter(student=student_profile, subject=subject, semester=semester).exists():
                messages.warning(request, 'أنت مسجل بالفعل في هذا المقرر')
            else:
                Result.objects.create(
                    student=student_profile,
                    subject=subject,
                    grade=0,
                    semester=semester,
                    specialty=student_profile.specialty or subject.specialty,
                    level=student_profile.level or subject.level,
                    section=student_profile.section or Section.objects.first() or Section.objects.get_or_create(sec_no=1, defaults={'sec_name': 'أقسام عامة'})[0]
                )
                messages.success(request, f'تم التسجيل في المقرر {subject.sub_name} بنجاح')
            return redirect('student_register')
        
        elif action == 'drop':
            result_record = get_object_or_404(Result, id=course_id, student=student_profile)
            sub_name = result_record.subject.sub_name
            result_record.delete()
            messages.success(request, f'تم إلغاء التسجيل من المقرر {sub_name}')
            return redirect('student_register')
    
    # المقررات المتاحة للتسجيل (المقررات في نفس مستوى وتخصص الطالب ولم يسجلها بعد)
    enrolled_subject_ids = Result.objects.filter(student=student_profile, semester=semester).values_list('subject_id', flat=True)
    
    available_subjects = Subject.objects.all()
    if student_profile.level:
        available_subjects = available_subjects.filter(level=student_profile.level)
    if student_profile.specialty:
        available_subjects = available_subjects.filter(specialty=student_profile.specialty)
        
    available_subjects = available_subjects.exclude(sub_no__in=enrolled_subject_ids)
    
    # المقررات المسجلة حالياً
    current_results = Result.objects.filter(student=student_profile, semester=semester).select_related('subject')
    
    # تحويل المسميات لتتوافق مع القالب
    formatted_available = [{'id': s.sub_no, 'name': s.sub_name, 'code': s.sub_no, 'credits': s.hours} for s in available_subjects]
    formatted_enrolled = [{'id': r.id, 'course': {'name': r.subject.sub_name, 'code': r.subject.sub_no, 'credits': r.subject.hours}} for r in current_results]
    
    context = {
        'available_courses': formatted_available,
        'current_enrollments': formatted_enrolled
    }
    return render(request, 'institute/dashboards/student_register.html', context)


@login_required(login_url='login')
def student_transcript_view(request):
    """السجل الأكاديمي للطالب"""
    if request.user.role != 'student':
        messages.error(request, 'ليس لديك صلاحية للوصول إلى هذه الصفحة')
        return redirect('dashboard')
    
    student_profile = get_or_create_profile(request.user)
    results = Result.objects.filter(student=student_profile).select_related('subject', 'semester')
    
    formatted_enrollments = []
    for r in results:
        formatted_enrollments.append({
            'course': {'name': r.subject.sub_name, 'code': r.subject.sub_no, 'credits': r.subject.hours},
            'attendance_grade': float(r.attendance_grade),
            'activity_grade': float(r.activity_grade),
            'midterm_grade': float(r.midterm_grade),
            'final_grade': float(r.final_grade),
            'grade': float(r.grade),
            'edit_reason': r.edit_reason or ''
        })
        
    context = {
        'enrollments': formatted_enrollments
    }
    return render(request, 'institute/dashboards/student_transcript.html', context)


# ============= وظائف أعضاء هيئة التدريس =============

@login_required(login_url='login')
def faculty_courses_view(request):
    """إدارة المقررات ورصد الدرجات"""
    if request.user.role != 'faculty':
        messages.error(request, 'ليس لديك صلاحية للوصول إلى هذه الصفحة')
        return redirect('dashboard')
    
    teacher_profile = get_or_create_profile(request.user)
    courses = Subject.objects.filter(teacher=teacher_profile)
    
    selected_course_id = request.GET.get('course_id')
    selected_course = None
    course_enrollments = []
    
    if selected_course_id:
        selected_course = get_object_or_404(Subject, sub_no=selected_course_id, teacher=teacher_profile)
    elif courses.exists():
        selected_course = courses.first()
        
    if request.method == 'POST':
        course_id = request.POST.get('course_id')
        subject = get_object_or_404(Subject, sub_no=course_id, teacher=teacher_profile)
        results = Result.objects.filter(subject=subject)
        
        for result in results:
            att_val = request.POST.get(f'attendance_score_{result.id}', '')
            act_val = request.POST.get(f'activity_score_{result.id}', '')
            mid_val = request.POST.get(f'midterm_score_{result.id}', '')
            fin_val = request.POST.get(f'final_score_{result.id}', '')
            reason = request.POST.get(f'edit_reason_{result.id}', '')
            
            try:
                attendance_score = float(att_val) if att_val else 0.0
                activity_score = float(act_val) if act_val else 0.0
                midterm_score = float(mid_val) if mid_val else 0.0
                final_score = float(fin_val) if fin_val else 0.0
                
                # تحديث فقط إذا كان هناك تغيير
                if (result.attendance_grade != attendance_score or 
                    result.activity_grade != activity_score or 
                    result.midterm_grade != midterm_score or 
                    result.final_grade != final_score):
                    
                    result.attendance_grade = attendance_score
                    result.activity_grade = activity_score
                    result.midterm_grade = midterm_score
                    result.final_grade = final_score
                    if reason:
                        result.edit_reason = reason
                    result.save()
            except ValueError:
                pass
        
        messages.success(request, 'تم تحديث الدرجات والمعدلات التلقائية بنجاح')
        return redirect(f'/faculty/courses/?course_id={course_id}')
    
    if selected_course:
        course_enrollments = Result.objects.filter(subject=selected_course).select_related('student__user')
        
    # تحويل التنسيقات لتتوافق مع القالب
    formatted_courses = [{'id': c.sub_no, 'name': c.sub_name, 'code': c.sub_no} for c in courses]
    
    formatted_enrollments = []
    for r in course_enrollments:
        formatted_enrollments.append({
            'id': r.id,
            'student': {'get_full_name': r.student.user.get_full_name() or r.student.user.username},
            'attendance_grade': float(r.attendance_grade),
            'activity_grade': float(r.activity_grade),
            'midterm_grade': float(r.midterm_grade),
            'final_grade': float(r.final_grade),
            'grade': float(r.grade),
            'edit_reason': r.edit_reason or ''
        })
        
    context = {
        'courses': formatted_courses,
        'selected_course': selected_course,
        'course_enrollments': formatted_enrollments
    }
    return render(request, 'institute/dashboards/faculty_courses.html', context)


# ============= وظائف الشؤون المالية =============

@login_required(login_url='login')
def finance_invoices_view(request):
    """إدارة الفواتير والرسوم"""
    if request.user.role != 'finance':
        messages.error(request, 'ليس لديك صلاحية للوصول إلى هذه الصفحة')
        return redirect('dashboard')
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        amount = request.POST.get('amount')
        description = request.POST.get('description')
        
        student_profile = get_object_or_404(StudentProfile, id=student_id)
        
        try:
            from datetime import date
            total_amt = float(amount)
            default_section = Section.objects.get_or_create(sec_no=1, defaults={'sec_name': 'عام'})[0]
            default_level   = SLevel.objects.get_or_create(lev_no=1, defaults={'lev_name': 'أول'})[0]
            default_spec    = Specialty.objects.filter(section=default_section, level=default_level).first() or \
                              Specialty.objects.get_or_create(spec_no=1, defaults={'spec_name': 'عام', 'level': default_level, 'section': default_section})[0]
            Fee.objects.create(
                student=student_profile,
                specialty=student_profile.specialty or default_spec,
                level=student_profile.level or default_level,
                total_fees=total_amt,
                paid=0,
                remaining=total_amt,
                due_date=date(2026, 12, 31),
            )
            messages.success(request, 'تم إنشاء الفاتورة بنجاح')
        except ValueError:
            messages.error(request, 'المبلغ غير صحيح')
            
        return redirect('finance_invoices')
    
    invoices = Fee.objects.all().select_related('student__user').order_by('-fee_no')
    students = StudentProfile.objects.all().select_related('user')
    
    # تحويل المسميات للواجهة
    formatted_invoices = []
    for inv in invoices:
        formatted_invoices.append({
            'student': {'get_full_name': inv.student.user.get_full_name() or inv.student.user.username},
            'amount': inv.total_fees,
            'description': f"رسوم دراسية تخصص {inv.specialty.spec_name}",
            'due_date': '2026-12-31',
            'status': 'paid' if inv.remaining == 0 else 'unpaid',
            'created_at': '2026-05-28'
        })
        
    formatted_students = []
    for s in students:
        formatted_students.append({
            'id': s.id,
            'get_full_name': s.user.get_full_name() or s.user.username
        })
        
    context = {
        'invoices': formatted_invoices,
        'students': formatted_students
    }
    return render(request, 'institute/dashboards/finance_invoices.html', context)


# ============= وظائف الرسائل =============

@login_required(login_url='login')
def messages_view(request):
    """الرسائل الداخلية"""
    user = request.user
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'send':
            receiver_id = request.POST.get('receiver_id')
            subject = request.POST.get('subject')
            body = request.POST.get('body')
            
            receiver = get_object_or_404(User, id=receiver_id)
            Message.objects.create(
                sender=user,
                receiver=receiver,
                subject=subject,
                body=body
            )
            messages.success(request, 'تم إرسال الرسالة بنجاح')
            return redirect('messages')
        
        elif action == 'mark_read':
            message_id = request.POST.get('message_id')
            msg = get_object_or_404(Message, id=message_id, receiver=user)
            msg.is_read = True
            msg.save()
            return redirect('messages')
    
    inbox = Message.objects.filter(receiver=user).select_related('sender').order_by('-created_at')
    users = User.objects.exclude(id=user.id)
    
    context = {
        'inbox': inbox,
        'users': users
    }
    return render(request, 'institute/dashboards/messages.html', context)

@login_required(login_url='login')
def manager_dashboard_api(request):
    """API endpoint providing manager dashboard data in JSON format"""
    user = request.user
    if user.role != 'manager':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # KPI data
    kpi_labels = ['المستخدمين', 'الطلاب', 'المدرسين', 'المقررات']
    kpi_values = [
        User.objects.count(),
        StudentProfile.objects.count(),
        TeacherProfile.objects.count(),
        Subject.objects.count()
    ]
    
    # Finance data
    finance_labels = ['المدفوع', 'المتبقي', 'المصروفات']
    paid_amount = Fee.objects.aggregate(Sum('paid'))['paid__sum'] or 0
    unpaid_amount = Fee.objects.aggregate(Sum('remaining'))['remaining__sum'] or 0
    total_expenses = Expense.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    finance_values = [float(paid_amount), float(unpaid_amount), float(total_expenses)]
    
    # Alerts
    alerts = []
    if unpaid_amount > 0:
        alerts.append(f'هناك مبالغ غير مدفوعة تتجاوز الصفر بقيمة {unpaid_amount}')
    if total_expenses > paid_amount:
        alerts.append('تنبيه: إجمالي المصروفات أعلى من المدفوعات!')
        
    data = {
        'kpi_labels': kpi_labels,
        'kpi_values': kpi_values,
        'finance_labels': finance_labels,
        'finance_values': finance_values,
        'alerts': alerts,
    }
    return JsonResponse(data)


@login_required(login_url='login')
def manager_dashboard_view(request):
    """Render manager dashboard HTML page with KPI and finance data."""
    user = request.user
    if user.role != 'manager':
        return redirect('dashboard')
    
    # Gather data
    total_users = User.objects.count()
    total_students = StudentProfile.objects.count()
    total_faculty = TeacherProfile.objects.count()
    total_subjects = Subject.objects.count()
    
    # Fees (Income)
    total_invoices = Fee.objects.count()
    paid_amount = Fee.objects.aggregate(Sum('paid'))['paid__sum'] or 0
    unpaid_amount = Fee.objects.aggregate(Sum('remaining'))['remaining__sum'] or 0
    
    # Expenses
    total_expenses = Expense.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    daily_withdrawn = Expense.objects.filter(expense_type='daily_withdrawal').aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Net Profit
    net_profit = paid_amount - total_expenses
    
    # Early Warning Alerts
    alerts = []
    if unpaid_amount > 0:
        alerts.append(f'تنبيه: هناك مبالغ غير مدفوعة (مستحقة) بقيمة {unpaid_amount} ريال يمني.')
    if total_faculty == 0:
        alerts.append('تحذير: لا يوجد أعضاء هيئة تدريس مسجلين.')
    if total_students == 0:
        alerts.append('تحذير: لا يوجد طلاب مسجلين في النظام.')
    if total_expenses > paid_amount:
        alerts.append('تنبيه مالي: إجمالي المصروفات يتجاوز الإيرادات المحصلة!')
        
    context = {
        'total_users': total_users,
        'total_students': total_students,
        'total_faculty': total_faculty,
        'total_subjects': total_subjects,
        'total_courses': total_subjects,
        'total_invoices': total_invoices,
        'paid_amount': paid_amount,
        'unpaid_amount': unpaid_amount,
        'total_expenses': total_expenses,
        'daily_withdrawn': daily_withdrawn,
        'net_profit': net_profit,
        'alerts': alerts,
    }
    return render(request, 'institute/dashboards/manager_dashboard.html', context)


@login_required(login_url='login')
def manager_search_view(request):
    """بوابة الاستعلام العام للمدير للبحث الموحد في النظام"""
    if request.user.role != 'manager':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'students': [], 'employees': [], 'teachers': [], 'finances': [], 'expenses': []})
    
    # البحث في الطلاب
    students_qs = StudentProfile.objects.filter(
        Q(user__username__icontains=q) |
        Q(user__first_name__icontains=q) |
        Q(user__last_name__icontains=q) |
        Q(st_address__icontains=q) |
        Q(specialty__spec_name__icontains=q)
    ).select_related('user', 'specialty', 'level')[:15]
    
    students = []
    for s in students_qs:
        students.append({
            'username': s.user.username,
            'name': s.user.get_full_name() or s.user.username,
            'specialty': s.specialty.spec_name if s.specialty else 'غير محدد',
            'level': s.level.lev_name if s.level else 'غير محدد',
            'status': s.status,
            'phone': s.user.phone or 'لا يوجد'
        })
        
    # البحث في الموظفين
    employees_qs = EmployeeProfile.objects.filter(
        Q(user__username__icontains=q) |
        Q(user__first_name__icontains=q) |
        Q(user__last_name__icontains=q) |
        Q(job_title__icontains=q)
    ).select_related('user', 'administration')[:15]
    
    employees = []
    for emp in employees_qs:
        employees.append({
            'name': emp.user.get_full_name() or emp.user.username,
            'job_title': emp.job_title,
            'admin_name': emp.administration.admin_name if emp.administration else 'غير محدد',
            'status': emp.status
        })
        
    # البحث في المدرسين
    teachers_qs = TeacherProfile.objects.filter(
        Q(user__username__icontains=q) |
        Q(user__first_name__icontains=q) |
        Q(user__last_name__icontains=q) |
        Q(qualification__icontains=q)
    ).select_related('user', 'specialty')[:15]
    
    teachers = []
    for t in teachers_qs:
        teachers.append({
            'name': t.user.get_full_name() or t.user.username,
            'specialty': t.specialty.spec_name if t.specialty else 'غير محدد',
            'qualification': t.qualification or 'غير محدد',
            'status': t.status
        })
        
    # البحث في الرسوم والوضع المالي للطلاب
    fees_qs = Fee.objects.filter(
        Q(student__user__first_name__icontains=q) |
        Q(student__user__last_name__icontains=q) |
        Q(student__user__username__icontains=q)
    ).select_related('student__user')[:15]
    
    finances = []
    for f in fees_qs:
        finances.append({
            'student_name': f.student.user.get_full_name() or f.student.user.username,
            'total_fees': float(f.total_fees),
            'paid': float(f.paid),
            'remaining': float(f.remaining),
            'status': 'مدفوع بالكامل' if f.remaining == 0 else 'متبقي'
        })
        
    # البحث في المصاريف
    expenses_qs = Expense.objects.filter(
        Q(description__icontains=q) |
        Q(recipient__icontains=q) |
        Q(expense_type__icontains=q)
    )[:15]
    
    expenses = []
    for exp in expenses_qs:
        expenses.append({
            'type': exp.get_expense_type_display(),
            'amount': float(exp.amount),
            'recipient': exp.recipient or 'غير محدد',
            'date': exp.date.strftime('%Y-%m-%d'),
            'description': exp.description
        })
        
    return JsonResponse({
        'students': students,
        'employees': employees,
        'teachers': teachers,
        'finances': finances,
        'expenses': expenses
    })


@login_required(login_url='login')
def finance_expenses_view(request):
    """إدارة المصروفات التشغيلية والمصروف اليومي وإيجار الطوابق"""
    if request.user.role not in ['finance', 'manager']:
        messages.error(request, 'ليس لديك صلاحية للوصول إلى المصروفات')
        return redirect('dashboard')
        
    if request.method == 'POST':
        expense_type = request.POST.get('expense_type')
        amount = request.POST.get('amount')
        recipient = request.POST.get('recipient')
        description = request.POST.get('description')
        
        try:
            amt = float(amount)
            Expense.objects.create(
                expense_type=expense_type,
                amount=amt,
                recipient=recipient,
                description=description
            )
            messages.success(request, 'تم تسجيل المصروف بنجاح')
        except ValueError:
            messages.error(request, 'يرجى إدخال مبلغ صحيح')
            
        return redirect('finance_expenses')
        
    expenses = Expense.objects.all().order_by('-date')
    total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # تصنيف المصاريف حسب الطابق والسحب اليومي
    floor1_rent = expenses.filter(expense_type='rent_floor1').aggregate(Sum('amount'))['amount__sum'] or 0
    floor2_rent = expenses.filter(expense_type='rent_floor2').aggregate(Sum('amount'))['amount__sum'] or 0
    daily_withdrawn = expenses.filter(expense_type='daily_withdrawal').aggregate(Sum('amount'))['amount__sum'] or 0
    
    context = {
        'expenses': expenses,
        'total_expenses': total_expenses,
        'floor1_rent': floor1_rent,
        'floor2_rent': floor2_rent,
        'daily_withdrawn': daily_withdrawn,
        'expense_types': ExpenseType.choices
    }
    return render(request, 'institute/dashboards/finance_expenses.html', context)


@login_required(login_url='login')
def finance_payments_view(request):
    """تسجيل أقساط الرسوم الدراسية للطلاب وتحديث المتبقي"""
    if request.user.role not in ['finance', 'manager']:
        messages.error(request, 'ليس لديك صلاحية لإجراء المدفوعات')
        return redirect('dashboard')
        
    if request.method == 'POST':
        fee_id = request.POST.get('fee_id')
        amount_paid = request.POST.get('amount_paid')
        receipt_no = request.POST.get('receipt_no')
        
        fee = get_object_or_404(Fee, fee_no=fee_id)
        try:
            amt = float(amount_paid)
            if amt <= 0:
                messages.error(request, 'يجب أن يكون المبلغ أكبر من صفر')
            elif amt > fee.remaining:
                messages.error(request, f'المبلغ المدفوع أكبر من المتبقي وهو: {fee.remaining}')
            else:
                FeePayment.objects.create(
                    fee=fee,
                    amount_paid=amt,
                    receipt_no=receipt_no,
                    received_by=request.user
                )
                messages.success(request, 'تم تسجيل القسط المالي بنجاح')
        except ValueError:
            messages.error(request, 'المبلغ غير صحيح')
        except Exception as e:
            messages.error(request, f'خطأ أثناء الحفظ: {e}')
            
    return redirect('finance_invoices')


@login_required(login_url='login')
def document_archive_view(request):
    """إدارة المستندات والأرشفة الإلكترونية وتتبع الأمان (EDMS)"""
    if request.user.role not in ['manager', 'admin', 'admission', 'staff']:
        messages.error(request, 'ليس لديك صلاحية للوصول للأرشيف الرقمي')
        return redirect('dashboard')
        
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'upload':
            title = request.POST.get('title')
            doc_type = request.POST.get('doc_type')
            file = request.FILES.get('file')
            student_id = request.POST.get('student_id')
            employee_id = request.POST.get('employee_id')
            
            student = None
            employee = None
            if student_id:
                student = get_object_or_404(StudentProfile, id=student_id)
            if employee_id:
                employee = get_object_or_404(EmployeeProfile, id=employee_id)
                
            if file:
                doc = Document.objects.create(
                    title=title,
                    file=file,
                    doc_type=doc_type,
                    student=student,
                    employee=employee,
                    uploaded_by=request.user
                )
                # تسجيل الحركة في سجل التتبع
                AuditTrail.objects.create(
                    user=request.user,
                    action=AuditAction.CREATE,
                    model_name='Document',
                    object_id=doc.doc_no,
                    details=f"تم رفع الوثيقة '{title}' من النوع '{doc_type}'"
                )
                messages.success(request, 'تم رفع الوثيقة بنجاح وأرشفتها')
            else:
                messages.error(request, 'يرجى اختيار ملف صالح')
                
        elif action == 'delete':
            doc_id = request.POST.get('doc_id')
            doc = get_object_or_404(Document, doc_no=doc_id)
            title = doc.title
            doc.file.delete()
            doc.delete()
            
            # تسجيل الحركة في سجل التتبع
            AuditTrail.objects.create(
                user=request.user,
                action=AuditAction.DELETE,
                model_name='Document',
                object_id=int(doc_id),
                details=f"تم حذف الوثيقة '{title}' نهائياً"
            )
            messages.success(request, 'تم حذف الوثيقة من الأرشيف بنجاح')
            
        return redirect('document_archive')
        
    q = request.GET.get('q', '').strip()
    documents = Document.objects.all().order_by('-created_at')
    if q:
        documents = documents.filter(
            Q(title__icontains=q) |
            Q(doc_type__icontains=q) |
            Q(student__user__first_name__icontains=q) |
            Q(student__user__last_name__icontains=q) |
            Q(employee__user__first_name__icontains=q) |
            Q(employee__user__last_name__icontains=q)
        )
        
    students = StudentProfile.objects.all().select_related('user')
    employees = EmployeeProfile.objects.all().select_related('user')
    audit_logs = AuditTrail.objects.all()[:50]
    
    context = {
        'documents': documents,
        'students': students,
        'employees': employees,
        'audit_logs': audit_logs,
        'search_query': q
    }
    return render(request, 'institute/dashboards/document_archive.html', context)

# ============================================================
#  الكنترول (Control Dashboard)
# ============================================================

from .models import ExamSchedule, ExamPaperTracking


@login_required(login_url='login')
def control_dashboard_view(request):
    if request.user.role not in ['control', 'manager']:
        messages.error(request, 'ليس لديك صلاحية للوصول إلى هذه الصفحة')
        return redirect('dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_schedule':
            try:
                subject = Subject.objects.get(pk=request.POST.get('subject'))
                schedule = ExamSchedule.objects.create(
                    subject=subject,
                    exam_date=request.POST.get('exam_date'),
                    start_time=request.POST.get('start_time'),
                    end_time=request.POST.get('end_time'),
                    hall_name=request.POST.get('hall_name'),
                )
                ExamPaperTracking.objects.create(schedule=schedule)
                messages.success(request, 'تم إضافة جدول الامتحان بنجاح.')
            except Exception as e:
                messages.error(request, f'حدث خطأ: {e}')

        elif action == 'delete_schedule':
            ExamSchedule.objects.filter(pk=request.POST.get('schedule_id')).delete()
            messages.success(request, 'تم حذف الامتحان.')

        elif action == 'update_tracking':
            try:
                t = ExamPaperTracking.objects.get(schedule__pk=request.POST.get('schedule_id'))
                t.questions_submitted  = request.POST.get('questions_submitted') == 'on'
                t.papers_printed       = request.POST.get('papers_printed') == 'on'
                t.delivered_to_hall    = request.POST.get('delivered_to_hall') == 'on'
                t.returned_from_hall   = request.POST.get('returned_from_hall') == 'on'
                t.delivered_to_teacher = request.POST.get('delivered_to_teacher') == 'on'
                t.returned_graded      = request.POST.get('returned_graded') == 'on'
                t.save()
                messages.success(request, 'تم تحديث حالة تتبع الأوراق بنجاح.')
            except Exception as e:
                messages.error(request, f'حدث خطأ: {e}')

        elif action == 'add_result':
            try:
                att   = float(request.POST.get('attendance_grade', 0))
                act   = float(request.POST.get('activity_grade', 0))
                mid   = float(request.POST.get('midterm_grade', 0))
                fin   = float(request.POST.get('final_grade', 0))
                total = att + act + mid + fin
                student = StudentProfile.objects.get(pk=request.POST.get('student_id'))
                subject = Subject.objects.get(pk=request.POST.get('subject_id'))
                result, created = Result.objects.get_or_create(
                    student=student, subject=subject,
                    defaults={
                        'attendance_grade': att, 'activity_grade': act,
                        'midterm_grade': mid, 'final_grade': fin, 'grade': total,
                        'edit_reason': 'ادخال من الكنترول',
                        'semester': getattr(subject, 'semester', None),
                        'specialty': getattr(subject, 'specialty', None),
                        'level': getattr(subject, 'level', None),
                        'section': None,
                    }
                )
                if not created:
                    result.attendance_grade = att
                    result.activity_grade   = act
                    result.midterm_grade    = mid
                    result.final_grade      = fin
                    result.grade            = total
                    result.edit_reason      = 'تحديث من الكنترول'
                    result.save()
                messages.success(request, f'تم حفظ النتيجة. (المجموع: {total})')
            except Exception as e:
                messages.error(request, f'حدث خطأ: {e}')
            return redirect('/control/dashboard/?tab=results')

        elif action == 'edit_result':
            try:
                att   = float(request.POST.get('attendance_grade', 0))
                act   = float(request.POST.get('activity_grade', 0))
                mid   = float(request.POST.get('midterm_grade', 0))
                fin   = float(request.POST.get('final_grade', 0))
                total = att + act + mid + fin
                result = Result.objects.get(pk=request.POST.get('result_no'))
                result.attendance_grade = att
                result.activity_grade   = act
                result.midterm_grade    = mid
                result.final_grade      = fin
                result.grade            = total
                result.edit_reason      = 'تعديل من الكنترول'
                result.save()
                messages.success(request, f'تم تعديل الدرجات. (المجموع: {total})')
            except Exception as e:
                messages.error(request, f'حدث خطأ: {e}')
            return redirect('/control/dashboard/?tab=results')

        elif action == 'bulk_approve':
            try:
                subject_id = request.POST.get('subject_id')
                if subject_id:
                    ExamPaperTracking.objects.filter(schedule__subject__sub_no=subject_id).update(results_approved=True)
                else:
                    ExamPaperTracking.objects.all().update(results_approved=True)
                messages.success(request, 'تم اعتماد النتائج بنجاح.')
            except Exception as e:
                messages.error(request, f'حدث خطأ: {e}')
            return redirect('/control/dashboard/?tab=results')

        return redirect('control_dashboard')

    # GET
    today        = timezone.now().date()
    exams        = ExamSchedule.objects.all().order_by('exam_date', 'start_time')
    todays_exams = exams.filter(exam_date=today)
    subjects     = Subject.objects.filter(is_active=True)
    students     = StudentProfile.objects.select_related('user').all()

    total_exams    = exams.count()
    pending_papers = ExamPaperTracking.objects.filter(returned_from_hall=True, returned_graded=False).count()
    approved_count = ExamPaperTracking.objects.filter(results_approved=True).count()

    filter_subject = request.GET.get('filter_subject', '')
    results_qs = Result.objects.select_related('student__user', 'subject').all()
    if filter_subject:
        results_qs = results_qs.filter(subject__sub_no=filter_subject)

    from django.db.models import Avg
    r_total  = results_qs.count()
    r_passed = results_qs.filter(grade__gte=50).count()
    r_failed = results_qs.filter(grade__lt=50).count()
    r_avg    = results_qs.aggregate(avg=Avg('grade'))['avg'] or 0

    context = {
        'exams': exams, 'todays_exams': todays_exams,
        'total_exams': total_exams, 'pending_papers': pending_papers,
        'approved_results': approved_count,
        'subjects': subjects, 'students': students,
        'results_list': results_qs, 'filter_subject': filter_subject,
        'results_stats': {'total': r_total, 'passed': r_passed, 'failed': r_failed, 'avg': r_avg},
    }
    return render(request, 'institute/dashboards/control_dashboard.html', context)
