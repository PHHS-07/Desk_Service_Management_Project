from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class ClientRequest(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    SERVICE_PROTOTYPE = 'prototype'
    SERVICE_WEB = 'web_development'
    SERVICE_MOBILE = 'mobile_app'
    SERVICE_UIUX = 'ui_ux'
    SERVICE_OTHER = 'other'

    SERVICE_CHOICES = [
        (SERVICE_PROTOTYPE, 'Prototype'),
        (SERVICE_WEB, 'Web Development'),
        (SERVICE_MOBILE, 'Mobile App'),
        (SERVICE_UIUX, 'UI/UX Design'),
        (SERVICE_OTHER, 'Other Service'),
    ]

    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='client_requests')
    project = models.ForeignKey(
        'Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='client_requests',
    )
    title = models.CharField(max_length=180)
    description = models.TextField()
    service_type = models.CharField(max_length=40, choices=SERVICE_CHOICES, default=SERVICE_PROTOTYPE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    admin_response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} - {self.client.username}'


class RequestAttachment(models.Model):
    request = models.ForeignKey(ClientRequest, on_delete=models.CASCADE, related_name='attachments')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    file = models.FileField(upload_to='request_attachments/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class Project(models.Model):
    STATUS_PLANNING = 'planning'
    STATUS_ACTIVE = 'active'
    STATUS_ON_HOLD = 'on_hold'
    STATUS_COMPLETED = 'completed'

    STATUS_CHOICES = [
        (STATUS_PLANNING, 'Planning'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_ON_HOLD, 'On Hold'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PLANNING)
    clients = models.ManyToManyField(User, blank=True, related_name='projects')
    managers = models.ManyToManyField(User, blank=True, related_name='managed_projects')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class ClientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
    mobile_number = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f'{self.user.username} profile'


class ManagerProfile(models.Model):
    ROLE_DEVELOPER = 'developer'
    ROLE_PM = 'project_manager'
    ROLE_TESTER = 'tester'
    ROLE_CHOICES = [
        (ROLE_DEVELOPER, 'Developer'),
        (ROLE_PM, 'Project Manager'),
        (ROLE_TESTER, 'Tester'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='manager_profile')
    mobile_number = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, blank=True)

    def __str__(self):
        return f'{self.user.username} manager profile'


class ActivityLog(models.Model):
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='activity_logs')
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='activity_logs')
    client = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='client_activity_logs')
    title = models.CharField(max_length=180)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Payment(models.Model):
    STATUS_UNPAID = 'unpaid'
    STATUS_PARTIAL = 'partial'
    STATUS_PAID = 'paid'
    STATUS_OVERDUE = 'overdue'

    STATUS_CHOICES = [
        (STATUS_UNPAID, 'Unpaid'),
        (STATUS_PARTIAL, 'Partial'),
        (STATUS_PAID, 'Paid'),
        (STATUS_OVERDUE, 'Overdue'),
    ]

    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
    )
    request = models.ForeignKey(
        ClientRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_UNPAID)
    date = models.DateField(default=timezone.localdate)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.client.username} - {self.amount} ({self.get_status_display()})'

    @property
    def remaining_amount(self):
        remaining = self.amount - self.paid_amount
        return remaining if remaining > 0 else 0


class PaymentProof(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_REVIEWED = 'reviewed'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Review'),
        (STATUS_REVIEWED, 'Reviewed'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_proofs')
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='proofs')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    proof_image = models.FileField(upload_to='payment_proofs/')
    note = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.client.username} proof for {self.payment_id}'
class ManagerQuery(models.Model):
    STATUS_SENT = 'sent'
    STATUS_READ = 'read'
    STATUS_ARCHIVED = 'archived'

    STATUS_CHOICES = [
        (STATUS_SENT, 'Sent'),
        (STATUS_READ, 'Read'),
        (STATUS_ARCHIVED, 'Archived'),
    ]

    manager = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admin_queries')
    title = models.CharField(max_length=180)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SENT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} - {self.manager.username}'
