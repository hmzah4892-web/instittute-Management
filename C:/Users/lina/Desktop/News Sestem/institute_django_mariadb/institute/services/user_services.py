from django.utils import timezone
from institute.models import User, StudentProfile, TeacherProfile, EmployeeProfile, Specialty, SLevel

def get_or_create_profile(user):
    """دالة مساعدة لإنشاء ملف تعريف للمستخدم تلقائياً إذا لم يكن موجوداً"""
    if not user.is_authenticated:
        return None
        
    if user.role == 'student':
        profile, created = StudentProfile.objects.get_or_create(
            user=user,
            defaults={'gender': 'ذكر', 'status': 'نشط'}
        )
        return profile
        
    elif user.role == 'faculty':
        profile, created = TeacherProfile.objects.get_or_create(
            user=user,
            defaults={'status': 'نشط', 'contract_date': timezone.now().date()}
        )
        return profile
        
    elif user.role in ['manager', 'admin', 'admission', 'finance', 'staff']:
        profile, created = EmployeeProfile.objects.get_or_create(
            user=user,
            defaults={
                'gender': 'ذكر',
                'hire_date': timezone.now().date(),
                'status': 'نشط',
                'job_title': user.get_role_display(),
            }
        )
        return profile
    return None

def create_system_user(username, password, full_name, email, role, **kwargs):
    """إنشاء مستخدم جديد مع ملفه التعريفي"""
    if User.objects.filter(username=username).exists():
        raise ValueError("اسم المستخدم موجود بالفعل")
        
    user = User.objects.create_user(
        username=username,
        password=password,
        first_name=full_name.split()[0] if full_name else '',
        last_name=' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else '',
        email=email,
        role=role
    )
    
    profile = get_or_create_profile(user)
    
    # تحديث البيانات الخاصة للطلاب
    if role == 'student' and profile:
        specialty_id = kwargs.get('specialty_id')
        level_id = kwargs.get('level_id')
        
        if specialty_id:
            profile.specialty = Specialty.objects.filter(spec_no=specialty_id).first()
        if level_id:
            profile.level = SLevel.objects.filter(lev_no=level_id).first()
            
        profile.st_address = kwargs.get('address', '')
        profile.qualification = kwargs.get('qualification', '')
        profile.parent_phone = kwargs.get('parent_phone', '')
        
        # تحديث رقم الهاتف العام
        phone = kwargs.get('phone', '')
        if phone:
            user.phone = phone
            user.save()
            
        # تحديث ولي الأمر إذا وجد الاسم
        parent_name = kwargs.get('parent_name', '')
        if parent_name:
            from institute.models import Parent
            parent, _ = Parent.objects.get_or_create(
                student=profile,
                defaults={'name': parent_name, 'phone': kwargs.get('parent_phone', '')}
            )
            # Update in case it existed
            parent.name = parent_name
            parent.phone = kwargs.get('parent_phone', '')
            parent.save()
            
        profile.save()
        
    return user

def update_system_user(user_id, full_name, email, role):
    """تحديث بيانات مستخدم موجود"""
    user = User.objects.get(id=user_id)
    user.first_name = full_name.split()[0] if full_name else ''
    user.last_name = ' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else ''
    user.email = email
    if role:
        user.role = role
    user.save()
    return user
