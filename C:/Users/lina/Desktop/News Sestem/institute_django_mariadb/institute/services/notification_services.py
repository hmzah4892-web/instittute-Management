"""
خدمات الإشعارات والتعميمات — Notification Service Layer
=======================================================
توفر واجهة موحدة لإرسال الإشعارات بأنواعها:
- إشعار فردي لمستخدم محدد
- تعميم لمجموعة (حسب الدور)
- تعميم عام لجميع المستخدمين
- إنذار موظف
"""
from django.db.models import Q
from institute.models import (
    Notification, User, NotificationType, RoleChoices
)


def send_notification(sender, recipient, title, body,
                      notif_type=NotificationType.INFO):
    """إرسال إشعار فردي لمستخدم محدد"""
    return Notification.objects.create(
        sender=sender,
        recipient=recipient,
        title=title,
        body=body,
        notif_type=notif_type,
    )


def send_role_broadcast(sender, target_role, title, body,
                        notif_type=NotificationType.CIRCULAR):
    """
    إرسال تعميم لكل أصحاب دور معين.
    مثال: إرسال تعميم لكل المدرسين أو لكل الموظفين.
    """
    users = User.objects.filter(role=target_role, is_active=True)
    notifications = []
    for user in users:
        notifications.append(Notification(
            sender=sender,
            recipient=user,
            title=title,
            body=body,
            notif_type=notif_type,
            target_role=target_role,
        ))
    return Notification.objects.bulk_create(notifications)


def send_broadcast(sender, title, body,
                   notif_type=NotificationType.CIRCULAR):
    """إرسال تعميم عام لجميع المستخدمين النشطين"""
    return Notification.objects.create(
        sender=sender,
        title=title,
        body=body,
        notif_type=notif_type,
        is_broadcast=True,
    )


def send_employee_warning(sender, recipient, title, body):
    """إرسال إنذار لموظف (مع نوع تحذير)"""
    return send_notification(
        sender=sender,
        recipient=recipient,
        title=f"⚠️ إنذار: {title}",
        body=body,
        notif_type=NotificationType.ALERT,
    )


def get_user_notifications(user, unread_only=False, limit=20):
    """
    جلب إشعارات المستخدم:
    - إشعاراته الفردية
    - التعميمات الموجهة لدوره
    - التعميمات العامة
    """
    q = Q(recipient=user) | Q(is_broadcast=True)
    if user.role:
        q |= Q(target_role=user.role, recipient__isnull=True)

    qs = Notification.objects.filter(q).distinct()
    if unread_only:
        qs = qs.exclude(
            Q(recipient=user, is_read=True)
        )
    return qs.order_by('-created_at')[:limit]


def get_unread_count(user):
    """عدد الإشعارات غير المقروءة"""
    q = Q(recipient=user, is_read=False) | Q(is_broadcast=True, is_read=False)
    if user.role:
        q |= Q(target_role=user.role, recipient__isnull=True, is_read=False)
    return Notification.objects.filter(q).distinct().count()


def mark_as_read(notification_id, user):
    """تعليم إشعار كمقروء"""
    notif = Notification.objects.filter(
        Q(notif_no=notification_id),
        Q(recipient=user) | Q(is_broadcast=True) | Q(target_role=user.role)
    ).first()
    if notif:
        notif.is_read = True
        notif.save(update_fields=['is_read'])
    return notif


def mark_all_as_read(user):
    """تعليم كل إشعارات المستخدم كمقروءة"""
    Notification.objects.filter(
        recipient=user, is_read=False
    ).update(is_read=True)
