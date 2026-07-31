"""
خدمات الشؤون المالية — Finance Service Layer
==============================================
تتولى العمليات المتعلقة بالأموال:
- رسوم الطلاب والأقساط
- المصروفات اليومية
- مراكز التكلفة (Cost Centers)
"""
from datetime import date
from django.db.models import Sum
from institute.models import (
    Fee, FeePayment, Expense, Section, SLevel, Specialty, CostCenter
)


def create_student_fee(student_profile, amount):
    """إنشاء فاتورة رسوم لطالب معين"""
    total_amt = float(amount)
    
    # الحصول على القسم والمستوى والتخصص الافتراضي أو الفعلي
    default_section = Section.objects.get_or_create(sec_no=1, defaults={'sec_name': 'عام'})[0]
    default_level   = SLevel.objects.get_or_create(lev_no=1, defaults={'lev_name': 'أول'})[0]
    default_spec    = Specialty.objects.filter(section=default_section, level=default_level).first() or \
                      Specialty.objects.get_or_create(spec_no=1, defaults={'spec_name': 'عام', 'level': default_level, 'section': default_section})[0]
                      
    return Fee.objects.create(
        student=student_profile,
        specialty=student_profile.specialty or default_spec,
        level=student_profile.level or default_level,
        total_fees=total_amt,
        paid=0,
        remaining=total_amt,
        due_date=date(2026, 12, 31),
    )


def process_fee_payment(fee_record, amount_paid, receipt_no, received_by):
    """معالجة دفع قسط وتحديث الرصيد"""
    amt = float(amount_paid)
    if amt <= 0:
        raise ValueError('يجب أن يكون المبلغ أكبر من صفر')
    if amt > fee_record.remaining:
        raise ValueError(f'المبلغ المدفوع أكبر من المتبقي وهو: {fee_record.remaining}')
        
    return FeePayment.objects.create(
        fee=fee_record,
        amount_paid=amt,
        receipt_no=receipt_no,
        received_by=received_by
    )


def record_expense(expense_type, amount, recipient, description, section_id=None):
    """تسجيل مصروف تشغيلي"""
    amt = float(amount)
    if amt <= 0:
        raise ValueError('يجب أن يكون المبلغ أكبر من صفر')
        
    section = None
    if section_id:
        section = Section.objects.filter(sec_no=section_id).first()
        
    return Expense.objects.create(
        expense_type=expense_type,
        amount=amt,
        recipient=recipient,
        description=description,
        section=section
    )


def get_cost_center_report():
    """تقرير مراكز التكلفة وإيجارات الطوابق"""
    cost_centers = CostCenter.objects.filter(is_active=True)
    report = []
    
    for center in cost_centers:
        expenses = center.get_total_expenses()
        revenue = center.get_related_revenue()
        
        report.append({
            'center_no': center.center_no,
            'name': center.name,
            'type': center.get_center_type_display(),
            'monthly_rent': float(center.monthly_rent),
            'total_expenses': float(expenses),
            'related_revenue': float(revenue),
            'balance': float(revenue - expenses),
        })
        
    return report
