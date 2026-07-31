from institute.models import Document, AuditTrail, AuditAction

def upload_and_archive_document(title, doc_type, file, student, employee, uploaded_by):
    """رفع وأرشفة مستند وتسجيله في سجل التتبع"""
    doc = Document.objects.create(
        title=title,
        file=file,
        doc_type=doc_type,
        student=student,
        employee=employee,
        uploaded_by=uploaded_by
    )
    
    # تسجيل الحركة في سجل التتبع
    AuditTrail.objects.create(
        user=uploaded_by,
        action=AuditAction.CREATE,
        model_name='Document',
        object_id=doc.doc_no,
        details=f"تم رفع الوثيقة '{title}' من النوع '{doc_type}'"
    )
    return doc

def delete_archived_document(document_id, user):
    """حذف مستند من الأرشيف وتوثيق الحذف"""
    doc = Document.objects.filter(doc_no=document_id).first()
    if not doc:
        raise ValueError('المستند غير موجود')
        
    title = doc.title
    doc.file.delete()
    doc.delete()
    
    # تسجيل الحركة في سجل التتبع
    AuditTrail.objects.create(
        user=user,
        action=AuditAction.DELETE,
        model_name='Document',
        object_id=int(document_id),
        details=f"تم حذف الوثيقة '{title}' نهائياً"
    )
    return title
