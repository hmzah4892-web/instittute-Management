from django.urls import path
from . import views

urlpatterns = [
    # المصادقة
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # لوحة التحكم
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # إدارة المستخدمين والأقسام (للمدير)
    path('manager/users/', views.manager_users_view, name='manager_users'),
    path('manager/departments/', views.manager_departments_view, name='manager_departments'),
    path('manager/dashboard/', views.manager_dashboard_view, name='manager_dashboard'),
    
    # الطلاب
    path('student/register/', views.student_register_view, name='student_register'),
    path('student/transcript/', views.student_transcript_view, name='student_transcript'),
    
    # القبول والتسجيل
    path('admission/students/', views.admission_students_view, name='admission_students'),
    
    # أعضاء هيئة التدريس
    path('faculty/courses/', views.faculty_courses_view, name='faculty_courses'),
    
    # الشؤون المالية
    path('finance/invoices/', views.finance_invoices_view, name='finance_invoices'),
    
    # الرسائل
    path('messages/', views.messages_view, name='messages'),
    
    # الإضافات الجديدة للبحث والمصروفات والأقساط والأرشفة
    path('manager/search/', views.manager_search_view, name='manager_search'),
    path('finance/expenses/', views.finance_expenses_view, name='finance_expenses'),
    path('finance/payments/', views.finance_payments_view, name='finance_payments'),
    path('archive/', views.document_archive_view, name='document_archive'),
    
    # بوابة الموظف والموارد البشرية
    path('employee/', views.employee_portal_view, name='employee_portal'),
    path('hr/dashboard/', views.hr_dashboard_view, name='hr_dashboard'),
    path('hr/leaves/', views.hr_leave_requests_view, name='hr_leave_requests'),
    path('hr/payroll/', views.hr_payroll_view, name='hr_payroll'),
    
    # الإشعارات
    path('notifications/', views.notifications_view, name='notifications'),
    
    # رئيس القسم
    path('department-head/', views.dept_head_dashboard_view, name='dept_head_dashboard'),
    
    # الكنترول
    path('control/dashboard/', views.control_dashboard_view, name='control_dashboard'),
    
    # API
    path('api/manager/dashboard/', views.manager_dashboard_api, name='manager_dashboard_api'),
]
