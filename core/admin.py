from django.contrib import admin
from .models import ActivityLog, ClientProfile, ClientRequest, ManagerProfile, Payment, PaymentProof, Project


@admin.register(ClientRequest)
class ClientRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'service_type', 'status', 'created_at')
    list_filter = ('status', 'service_type', 'created_at')
    search_fields = ('title', 'description', 'client__username', 'client__email')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('client', 'request', 'amount', 'status', 'date')
    list_filter = ('status', 'date')
    search_fields = ('client__username', 'client__email', 'request__title')


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'description', 'clients__username', 'clients__email')
    filter_horizontal = ('clients', 'managers')


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'mobile_number')
    search_fields = ('user__username', 'user__email', 'mobile_number')


@admin.register(ManagerProfile)
class ManagerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'mobile_number')
    search_fields = ('user__username', 'user__email', 'mobile_number')


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('title', 'actor', 'project', 'client', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('title', 'details', 'actor__username', 'project__name', 'client__username')


@admin.register(PaymentProof)
class PaymentProofAdmin(admin.ModelAdmin):
    list_display = ('client', 'payment', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('client__username', 'payment__project__name')
