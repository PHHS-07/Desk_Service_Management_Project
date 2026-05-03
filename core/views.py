from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponseForbidden
from django.http import HttpResponse, JsonResponse
import io
import zipfile
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import mm
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
import logging

from .forms import (
    AdminRequestUpdateForm,
    AdminClientCreateForm,
    ClientEditForm,
    ClientPaymentProofForm,
    ClientRequestForm,
    ClientSignupForm,
    LoginForm,
    ManagerCreateForm,
    ManagerEditForm,
    PaymentForm,
    PaymentReceiveForm,
    PaymentRequestForm,
    ProjectForm,
)
from .models import ActivityLog, ClientRequest, ManagerQuery, Payment, PaymentProof, Project, RequestAttachment


def is_admin_user(user):
    return user.is_authenticated and user.is_superuser


def is_manager_user(user):
    return user.is_authenticated and user.is_staff and not user.is_superuser


def is_admin_or_manager(user):
    return user.is_authenticated and user.is_staff


def log_event(actor, title, details='', project=None, client=None):
    ActivityLog.objects.create(
        actor=actor if actor and actor.is_authenticated else None,
        title=title,
        details=details,
        project=project,
        client=client,
    )


def dashboard_redirect(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if is_admin_user(request.user):
        return redirect('admin_dashboard')
    if is_manager_user(request.user):
        return redirect('manager_dashboard')
    return redirect('client_dashboard')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')

    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password'],
        )
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_short_name() or user.username}.')
            return redirect('dashboard_redirect')
        messages.error(request, 'Invalid username or password.')

    return render(request, 'core/login.html', {'form': form})


def signup_view(request):
    messages.info(request, 'Client accounts are created by the admin team.')
    return redirect('login')


def username_available(request):
    """AJAX endpoint: ?username=... -> {available: bool} """
    username = (request.GET.get('username') or '').strip()
    if not username:
        return JsonResponse({'available': False})
    exists = User.objects.filter(username__iexact=username).exists()
    return JsonResponse({'available': not exists})


def build_password_reset_url(request, uid, token):
    path = reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
    host = settings.PASSWORD_RESET_DOMAIN
    protocol = settings.PASSWORD_RESET_PROTOCOL
    return f"{protocol}://{host}{path}"


def send_client_access_email(request, user, password=None):
    logger = logging.getLogger(__name__)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = build_password_reset_url(request, uid, token)
    password_line = f"Temporary password: {password}\n" if password else ''
    message_body = (
        f"Hello {user.get_full_name() or user.username},\n\n"
        f"Username: {user.username}\n"
        f"{password_line}"
        f"Password reset link: {reset_url}\n\n"
        "Please reset your password after login."
    )
    try:
        send_mail(
            subject='Your Roriri Project Desk account',
            message=message_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info('Access email sent to %s', user.email)
        return True
    except Exception:
        logger.exception('Failed to send access email to %s', user.email)
        return False


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


@login_required
@user_passes_test(is_admin_user, login_url='client_dashboard')
def admin_dashboard(request):
    clients = User.objects.filter(is_staff=False, is_superuser=False).order_by('-date_joined')
    requests = ClientRequest.objects.select_related('client').all()
    projects = Project.objects.all()
    payments = Payment.objects.select_related('client', 'request').all()
    status_counts = requests.values('status').annotate(total=Count('id'))
    payment_total = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    paid_total = payments.filter(status=Payment.STATUS_PAID).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    received_total = payments.aggregate(total=Sum('paid_amount'))['total'] or Decimal('0.00')
    remaining_total = payment_total - received_total

    monthly_income_qs = list(
        payments.annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(total=Sum('paid_amount'))
        .order_by('month')
    )
    
    # Process for template
    clean_monthly = [{'month': item['month'], 'total': item['total'] or Decimal('0.00')} for item in monthly_income_qs]
    max_income = max((item['total'] for item in clean_monthly), default=Decimal('1.00'))
    if max_income == Decimal('0.00'): max_income = Decimal('1.00')

    monthly_income = []
    for item in clean_monthly[-6:]: # Last 6 months
        if item['month']:
            monthly_income.append({
                'month': item['month'].strftime('%b'),
                'total': float(item['total']),
                'percent': float((item['total'] / max_income) * 100)
            })

    context = {
        'clients': clients[:8],
        'requests': requests,
        'payments': payments[:8],
        'monthly_income': monthly_income,
        'stats': {
            'clients': clients.count(),
            'total_projects': projects.count(),
            'active_projects': projects.exclude(status=Project.STATUS_COMPLETED).count(),
            'completed_projects': projects.filter(status=Project.STATUS_COMPLETED).count(),
            'payment_total': payment_total,
            'paid_total': paid_total,
            'received_total': received_total,
            'remaining_total': remaining_total,
        },
        'status_counts': {item['status']: item['total'] for item in status_counts},
        'active_nav': 'dashboard',
    }
    return render(request, 'core/admin_dashboard.html', context)


@login_required
@user_passes_test(is_admin_user, login_url='client_dashboard')
def admin_clients(request):
    form = AdminClientCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        # use provided/generated password from form if present, else generate random
        provided_pwd = form.cleaned_data.get('password1')
        password = provided_pwd if provided_pwd else get_random_string(10)
        user = form.save(commit=False)
        # ensure password is set to the expected value
        user.set_password(password)
        user.save()
        form.save_m2m() if hasattr(form, 'save_m2m') else None
        from core.models import ClientProfile, Project
        ClientProfile.objects.update_or_create(
            user=user,
            defaults={'mobile_number': form.cleaned_data['mobile_number']},
        )
        project_action = form.cleaned_data.get('project_action')
        if project_action == form.PROJECT_CREATE:
            Project.objects.create(name=f"{form.cleaned_data['name']}'s Project", description='Created from Add Client.', status=Project.STATUS_ACTIVE).clients.add(user)
        elif project_action:
            project = Project.objects.filter(pk=project_action).first()
            if project:
                project.clients.add(user)
        email_sent = False
        if user.email:
            email_sent = send_client_access_email(request, user, password)
        log_event(request.user, 'Client created', f'Created client {user.get_full_name() or user.username}.', client=user)
        if email_sent:
            messages.success(request, 'Client account created and access email sent.')
        else:
            messages.success(request, 'Client account created.')
            if user.email:
                messages.error(request, f'Failed to send access email to {user.email}.')
        return redirect('admin_clients')
    elif request.method == 'POST' and not form.is_valid():
        # surface validation errors to admin
        messages.error(request, f'Client creation failed: {form.errors.as_json()}')

    clients = User.objects.filter(is_staff=False, is_superuser=False).order_by('-date_joined')
    client_rows = []
    for client in clients:
        client_requests = client.client_requests.all()
        client_payments = client.payments.all()
        client_rows.append({
            'user': client,
            'mobile_number': getattr(getattr(client, 'client_profile', None), 'mobile_number', ''),
            'projects': client.projects.all(),
            'request_count': client_requests.count(),
            'latest_request': client_requests.first(),
            'payment_count': client_payments.count(),
        })

    return render(
        request,
        'core/admin_clients.html',
        {'form': form, 'client_rows': client_rows, 'active_nav': 'clients'},
    )


@login_required
@user_passes_test(is_admin_user, login_url='client_dashboard')
def admin_client_edit(request, pk):
    client = get_object_or_404(User, pk=pk, is_staff=False, is_superuser=False)
    form = ClientEditForm(request.POST or None, instance=client)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_event(request.user, 'Client updated', f'Updated client {client.get_full_name() or client.username}.', client=client)
        messages.success(request, 'Client details updated.')
        return redirect('admin_clients')
    return render(request, 'core/admin_client_edit.html', {'form': form, 'client': client, 'active_nav': 'clients'})


@login_required
@user_passes_test(is_admin_user, login_url='client_dashboard')
def admin_client_send_reset(request, pk):
    client = get_object_or_404(User, pk=pk, is_staff=False, is_superuser=False)
    if request.method != 'POST':
        return HttpResponseForbidden('POST required')
    if client.email:
        sent = send_client_access_email(request, client)
        if sent:
            log_event(request.user, 'Password reset sent', f'Sent password reset link to {client.email}.', client=client)
            messages.success(request, 'Password reset link sent to client email.')
        else:
            messages.error(request, f'Failed to send password reset link to {client.email}.')
    else:
        messages.error(request, 'Client does not have an email address.')
    return redirect('admin_clients')


@login_required
@user_passes_test(is_admin_user, login_url='client_dashboard')
def admin_manager_send_reset(request, pk):
    manager = get_object_or_404(User, pk=pk, is_staff=True, is_superuser=False)
    if request.method != 'POST':
        return HttpResponseForbidden('POST required')
    if manager.email:
        sent = send_client_access_email(request, manager)
        if sent:
            log_event(request.user, 'Password reset sent', f'Sent password reset link to {manager.email}.', client=manager)
            messages.success(request, 'Password reset link sent to manager email.')
        else:
            messages.error(request, f'Failed to send password reset link to {manager.email}.')
    else:
        messages.error(request, 'Manager does not have an email address.')
    return redirect('admin_managers')


@login_required
@user_passes_test(is_admin_user, login_url='client_dashboard')
def admin_client_delete(request, pk):
    client = get_object_or_404(User, pk=pk, is_staff=False, is_superuser=False)
    if request.method != 'POST':
        return HttpResponseForbidden('POST required')
    client_name = client.get_full_name() or client.username
    log_event(request.user, 'Client deleted', f'Deleted client {client_name}.')
    client.delete()
    messages.success(request, f'{client_name} deleted.')
    return redirect('admin_clients')


@login_required
@user_passes_test(is_admin_user, login_url='client_dashboard')
def admin_projects(request):
    form = ProjectForm(request.POST or None)
    manager_form = ManagerCreateForm()
    if request.method == 'POST' and form.is_valid():
        project = form.save()
        project.managers.add(*User.objects.filter(is_superuser=True))
        log_event(request.user, 'Project created', f'Created project {project.name}.', project=project)
        messages.success(request, 'Project created.')
        return redirect('admin_projects')

    if request.method == 'POST' and request.POST.get('form_type') == 'manager':
        manager_form = ManagerCreateForm(request.POST)
        if manager_form.is_valid():
            # compute password used (from form or generated fallback) so we can email it
            provided_pwd = manager_form.cleaned_data.get('password1')
            name_value = (manager_form.cleaned_data.get('name') or '').strip()
            mobile = manager_form.cleaned_data.get('mobile_number') or ''
            if provided_pwd:
                password = provided_pwd
            else:
                digits = ''.join(ch for ch in (mobile or '') if ch.isdigit())
                last4 = digits[-4:] if digits else ''
                password = f"{name_value}@{last4}" if last4 else f"{name_value}@{get_random_string(4)}"
            manager = manager_form.save()
            email_sent = False
            if manager.email:
                email_sent = send_client_access_email(request, manager, password)
            log_event(request.user, 'Manager created', f'Created managerial role {manager.get_full_name() or manager.username}.')
            if email_sent:
                messages.success(request, 'Managerial role created and access email sent.')
            else:
                messages.success(request, 'Managerial role created.')
                if manager.email:
                    messages.error(request, f'Failed to send access email to {manager.email}.')
            return redirect('admin_projects')
        else:
            messages.error(request, f'Manager creation failed: {manager_form.errors.as_json()}')

    projects = Project.objects.prefetch_related('clients', 'managers').all()
    return render(
        request,
        'core/admin_projects.html',
        {'form': form, 'manager_form': manager_form, 'projects': projects, 'active_nav': 'projects'},
    )


@login_required
@user_passes_test(is_admin_user, login_url='client_dashboard')
def admin_managers(request):
    form = ManagerCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        provided_pwd = form.cleaned_data.get('password1')
        name_value = (form.cleaned_data.get('name') or '').strip()
        mobile = form.cleaned_data.get('mobile_number') or ''
        if provided_pwd:
            password = provided_pwd
        else:
            digits = ''.join(ch for ch in (mobile or '') if ch.isdigit())
            last4 = digits[-4:] if digits else ''
            password = f"{name_value}@{last4}" if last4 else f"{name_value}@{get_random_string(4)}"
        manager = form.save()
        email_sent = False
        if manager.email:
            email_sent = send_client_access_email(request, manager, password)
        log_event(request.user, 'Manager created', f'Created manager {manager.get_full_name() or manager.username}.')
        if email_sent:
            messages.success(request, 'Manager created and access email sent.')
        else:
            messages.success(request, 'Manager created.')
            if manager.email:
                messages.error(request, f'Failed to send access email to {manager.email}.')
        return redirect('admin_managers')
    elif request.method == 'POST' and not form.is_valid():
        messages.error(request, f'Manager creation failed: {form.errors.as_json()}')

    managers = User.objects.filter(is_staff=True, is_superuser=False).prefetch_related('managed_projects').order_by('-date_joined')
    return render(
        request,
        'core/admin_managers.html',
        {'form': form, 'managers': managers, 'active_nav': 'managers'},
    )


@login_required
@user_passes_test(is_admin_user, login_url='client_dashboard')
def admin_manager_edit(request, pk):
    manager = get_object_or_404(User, pk=pk, is_staff=True, is_superuser=False)
    form = ManagerEditForm(request.POST or None, instance=manager)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_event(request.user, 'Manager updated', f'Updated manager {manager.get_full_name() or manager.username}.')
        messages.success(request, 'Manager updated.')
        return redirect('admin_managers')
    return render(request, 'core/admin_manager_edit.html', {'form': form, 'manager': manager, 'active_nav': 'managers'})


@login_required
@user_passes_test(is_admin_user, login_url='client_dashboard')
def admin_manager_delete(request, pk):
    manager = get_object_or_404(User, pk=pk, is_staff=True, is_superuser=False)
    if request.method != 'POST':
        return HttpResponseForbidden('POST required')
    name = manager.get_full_name() or manager.username
    log_event(request.user, 'Manager deleted', f'Deleted manager {name}.')
    manager.delete()
    messages.success(request, f'{name} deleted.')
    return redirect('admin_managers')


@login_required
@user_passes_test(is_admin_user, login_url='client_dashboard')
def admin_project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)
    form = ProjectForm(request.POST or None, instance=project)
    if request.method == 'POST' and form.is_valid():
        project = form.save()
        project.managers.add(*User.objects.filter(is_superuser=True))
        project.clients.remove(*User.objects.filter(is_superuser=True))
        log_event(request.user, 'Project updated', f'Updated project {project.name}.', project=project)
        messages.success(request, 'Project updated.')
        return redirect('admin_projects')
    return render(request, 'core/admin_project_edit.html', {'form': form, 'project': project, 'active_nav': 'projects'})


@login_required
@user_passes_test(is_admin_user, login_url='client_dashboard')
def admin_project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method != 'POST':
        return HttpResponseForbidden('POST required')
    project_name = project.name
    log_event(request.user, 'Project deleted', f'Deleted project {project_name}.')
    project.delete()
    messages.success(request, f'{project_name} deleted.')
    return redirect('admin_projects')


@login_required
@user_passes_test(is_admin_user, login_url='client_dashboard')
def admin_requests(request):
    requests = ClientRequest.objects.select_related('client', 'project').prefetch_related('project__managers').all()
    client_id = request.GET.get('client')
    project_id = request.GET.get('project')
    manager_id = request.GET.get('manager')
    sort = request.GET.get('sort', 'recent')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if client_id:
        requests = requests.filter(client_id=client_id)
    if project_id:
        requests = requests.filter(project_id=project_id)
    if manager_id:
        requests = requests.filter(project__managers__id=manager_id)
    if date_from:
        requests = requests.filter(created_at__date__gte=date_from)
    if date_to:
        requests = requests.filter(created_at__date__lte=date_to)
    if sort == 'oldest':
        requests = requests.order_by('created_at')
    else:
        requests = requests.order_by('-created_at')
    return render(
        request,
        'core/admin_requests.html',
        {
            'requests': requests,
            'clients': User.objects.filter(is_staff=False, is_superuser=False),
            'projects': Project.objects.all(),
            'managers': User.objects.filter(is_staff=True, is_superuser=False),
            'active_nav': 'requests',
        },
    )


@login_required
@user_passes_test(is_admin_user, login_url='client_dashboard')
def admin_request_detail(request, pk):
    client_request = get_object_or_404(ClientRequest.objects.select_related('client', 'project').prefetch_related('project__managers'), pk=pk)
    form = AdminRequestUpdateForm(instance=client_request)
    return render(
        request,
        'core/admin_request_detail.html',
        {'client_request': client_request, 'form': form, 'active_nav': 'requests', 'has_attachments': client_request.attachments.exists()},
    )


@login_required
@user_passes_test(is_admin_user, login_url='client_dashboard')
def admin_request_update(request, pk):
    client_request = get_object_or_404(ClientRequest, pk=pk)
    form = AdminRequestUpdateForm(request.POST or None, request.FILES or None, instance=client_request)
    if request.method == 'POST' and form.is_valid():
        client_request = form.save()
        upload = form.cleaned_data.get('upload_file')
        if upload:
            RequestAttachment.objects.create(request=client_request, uploaded_by=request.user, file=upload)
        log_event(
            request.user,
            'Request updated',
            f'Updated request {client_request.title} to {client_request.get_status_display()}.',
            project=client_request.project,
            client=client_request.client,
        )
        messages.success(request, 'Request status and response updated.')
        return redirect('admin_request_detail', pk=client_request.pk)
    return render(
        request,
        'core/admin_request_detail.html',
        {'client_request': client_request, 'form': form, 'active_nav': 'requests'},
    )


@login_required
@user_passes_test(is_admin_user, login_url='client_dashboard')
def admin_payments(request):
    request_form = PaymentRequestForm()
    receive_form = PaymentReceiveForm()

    if request.method == 'POST' and request.POST.get('form_type') == 'request':
        request_form = PaymentRequestForm(request.POST)
        if request_form.is_valid():
            request_form.save()
            messages.success(request, 'Payment request created.')
            return redirect('admin_payments')

    if request.method == 'POST' and request.POST.get('form_type') == 'receive':
        receive_form = PaymentReceiveForm(request.POST)
        if receive_form.is_valid():
            payment = receive_form.cleaned_data['payment']
            payment.paid_amount += receive_form.cleaned_data['amount']
            if payment.paid_amount >= payment.amount:
                payment.paid_amount = payment.amount
                payment.status = Payment.STATUS_PAID
            elif payment.paid_amount > 0:
                payment.status = Payment.STATUS_PARTIAL
            payment.notes = receive_form.cleaned_data.get('notes') or payment.notes
            payment.date = receive_form.cleaned_data['date']
            payment.save()
            log_event(request.user, 'Payment recorded', f'Recorded payment for {payment.client}.', project=payment.project, client=payment.client)
            messages.success(request, 'Payment received and balance updated.')
            return redirect('admin_payments')

    payments = Payment.objects.select_related('client', 'project', 'request').all()
    ledger_client = request.GET.get('ledger_client', '')
    ledger_payments = payments.filter(paid_amount__gt=0)
    if ledger_client:
        ledger_payments = ledger_payments.filter(client_id=ledger_client)
    proofs = PaymentProof.objects.select_related('client', 'payment', 'payment__project').all()
    stats = {
        'requested': payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
        'received': payments.aggregate(total=Sum('paid_amount'))['total'] or Decimal('0.00'),
    }
    stats['remaining'] = stats['requested'] - stats['received']
    # admin ledger PDF download
    if request.GET.get('download') == 'ledger':
        from io import BytesIO

        def generate_ledger_pdf(payments_qs, title):
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
            styles = getSampleStyleSheet()
            elems = [Paragraph(title, styles['Title']), Spacer(1, 12)]
            data = [['Date', 'Client', 'Project', 'Purpose', 'Paid', 'Status']]
            for p in payments_qs:
                date_str = p.date.strftime('%d %b %Y') if getattr(p, 'date', None) else ''
                client_name = p.client.get_full_name() or p.client.username
                proj = p.project.name if getattr(p, 'project', None) else 'No project'
                purpose = p.request.title if getattr(p, 'request', None) else 'General payment'
                data.append([date_str, client_name, proj, purpose, f'₹{p.paid_amount}', p.get_status_display()])
            table = Table(data, colWidths=[60,120,120,140,60,60])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (4, 1), (4, -1), 'RIGHT'),
            ]))
            elems.append(table)
            doc.build(elems)
            pdf = buffer.getvalue()
            buffer.close()
            return pdf

        # if ledger_client filter provided, ledger_payments already filtered above
        client_label = 'All clients'
        if ledger_client:
            client_obj = User.objects.filter(pk=ledger_client).first()
            client_label = client_obj.get_full_name() or client_obj.username if client_obj else client_label
        pdf_bytes = generate_ledger_pdf(ledger_payments, f"Ledger - {client_label}")
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="admin_ledger_{ledger_client or "all"}.pdf"'
        return response

    return render(
        request,
        'core/admin_payments.html',
        {
            'request_form': request_form,
            'receive_form': receive_form,
            'payments': payments,
            'proofs': proofs,
            'ledger_clients': User.objects.filter(payments__paid_amount__gt=0).distinct(),
            'ledger_payments': ledger_payments,
            'selected_ledger_client': ledger_client,
            'stats': stats,
            'active_nav': 'payments',
        },
    )


@login_required
@user_passes_test(is_admin_user, login_url='client_dashboard')
def admin_payment_update(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in dict(Payment.STATUS_CHOICES):
            payment.status = status
            payment.save(update_fields=['status'])
            messages.success(request, 'Payment status updated.')
        else:
            messages.error(request, 'Invalid payment status.')
    return redirect('admin_payments')


@login_required
@user_passes_test(is_admin_user, login_url='client_dashboard')
def admin_payment_proof_review(request, pk):
    proof = get_object_or_404(PaymentProof, pk=pk)
    if request.method != 'POST':
        return HttpResponseForbidden('POST required')
    action = request.POST.get('action')
    if action == 'reviewed':
        proof.status = PaymentProof.STATUS_REVIEWED
        log_event(request.user, 'Payment proof reviewed', f'Reviewed payment proof #{proof.pk}.', project=proof.payment.project, client=proof.client)
        messages.success(request, 'Payment proof marked as reviewed. Use Add Payment to record the received amount.')
    elif action == 'rejected':
        proof.status = PaymentProof.STATUS_REJECTED
        log_event(request.user, 'Payment proof rejected', f'Rejected payment proof #{proof.pk}.', project=proof.payment.project, client=proof.client)
        messages.success(request, 'Payment proof rejected.')
    proof.save(update_fields=['status'])
    return redirect('admin_payments')


@login_required
@user_passes_test(is_admin_or_manager, login_url='client_dashboard')
def logs_view(request):
    if is_admin_user(request.user):
        logs = ActivityLog.objects.select_related('actor', 'project', 'client').all()
        template = 'core/logs.html'
    else:
        projects = request.user.managed_projects.all()
        project_clients = User.objects.filter(projects__in=projects).distinct()
        logs = ActivityLog.objects.select_related('actor', 'project', 'client').filter(project__in=projects) | ActivityLog.objects.select_related('actor', 'project', 'client').filter(client__in=project_clients)
        template = 'core/logs.html'
    return render(request, template, {'logs': logs, 'active_nav': 'logs'})


@login_required
@user_passes_test(is_manager_user, login_url='admin_dashboard')
def manager_dashboard(request):
    projects = request.user.managed_projects.prefetch_related('clients').all()
    requests = ClientRequest.objects.filter(project__in=projects).select_related('client', 'project')
    return render(
        request,
        'core/manager_dashboard.html',
        {
            'projects': projects,
            'requests': requests[:6],
            'stats': {
                'projects': projects.count(),
                'requests': requests.count(),
                'pending': requests.filter(status=ClientRequest.STATUS_PENDING).count(),
                'completed': requests.filter(status=ClientRequest.STATUS_COMPLETED).count(),
            },
            'active_nav': 'dashboard',
        },
    )


@login_required
@user_passes_test(is_manager_user, login_url='admin_dashboard')
def manager_projects(request):
    return render(
        request,
        'core/manager_projects.html',
        {'projects': request.user.managed_projects.prefetch_related('clients').all(), 'active_nav': 'projects'},
    )


@login_required
@user_passes_test(is_manager_user, login_url='admin_dashboard')
def manager_requests(request):
    projects = request.user.managed_projects.all()
    requests = ClientRequest.objects.filter(project__in=projects).select_related('client', 'project')
    return render(
        request,
        'core/admin_requests.html',
        {
            'requests': requests,
            'clients': User.objects.filter(client_requests__project__in=projects).distinct(),
            'projects': projects,
            'managers': User.objects.filter(pk=request.user.pk),
            'active_nav': 'requests',
            'manager_mode': True,
        },
    )


@login_required
@user_passes_test(is_manager_user, login_url='admin_dashboard')
def manager_request_detail(request, pk):
    client_request = get_object_or_404(
        ClientRequest.objects.select_related('client', 'project').prefetch_related('project__managers'),
        pk=pk,
        project__managers=request.user,
    )
    form = AdminRequestUpdateForm(request.POST or None, request.FILES or None, instance=client_request)
    if request.method == 'POST' and form.is_valid():
        client_request = form.save()
        upload = form.cleaned_data.get('upload_file')
        if upload:
            RequestAttachment.objects.create(request=client_request, uploaded_by=request.user, file=upload)
        log_event(
            request.user,
            'Manager response sent',
            f'{request.user.get_full_name() or request.user.username} responded to request {client_request.title}.',
            project=client_request.project,
            client=client_request.client,
        )
        messages.success(request, 'Client request updated.')
        return redirect('manager_request_detail', pk=client_request.pk)
    return render(
        request,
        'core/admin_request_detail.html',
        {'client_request': client_request, 'form': form, 'active_nav': 'requests', 'manager_mode': True, 'has_attachments': client_request.attachments.exists()},
    )


@login_required
@user_passes_test(lambda u: u.is_authenticated, login_url='login')
def request_attachments_download(request, pk):
    client_request = get_object_or_404(ClientRequest, pk=pk)
    if not (
        request.user.is_superuser
        or (request.user.is_staff and client_request.project and client_request.project.managers.filter(pk=request.user.pk).exists())
        or client_request.client_id == request.user.pk
    ):
        return HttpResponseForbidden('Not allowed')
    attachments = list(client_request.attachments.all())
    if not attachments:
        return HttpResponseForbidden('No attachments found')
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for attachment in attachments:
            if attachment.file:
                file_name = attachment.file.name.split('/')[-1]
                attachment.file.open('rb')
                try:
                    zf.writestr(file_name, attachment.file.read())
                finally:
                    attachment.file.close()
    memory_file.seek(0)
    response = HttpResponse(memory_file.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="request_{client_request.pk}_attachments.zip"'
    return response


@login_required
def client_dashboard(request):
    if is_admin_user(request.user):
        return redirect('admin_dashboard')

    requests = request.user.client_requests.all()
    payments = request.user.payments.select_related('request').all()
    requested = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    paid = payments.aggregate(total=Sum('paid_amount'))['total'] or Decimal('0.00')
    projects = Project.objects.filter(clients=request.user).prefetch_related('clients')
    selected_project = request.GET.get('project', '')
    selected_project_obj = None
    if selected_project:
        selected_project_obj = projects.filter(pk=selected_project).first()

    project_history = []
    for project in projects:
        project_requests = requests.filter(project=project)
        project_payments = payments.filter(project=project)
        project_history.append({
            'project': project,
            'requests': project_requests,
            'payments': project_payments,
            'request_count': project_requests.count(),
            'completed_count': project_requests.filter(status=ClientRequest.STATUS_COMPLETED).count(),
            'remaining_total': sum((payment.remaining_amount for payment in project_payments), Decimal('0.00')),
        })
    roadmap_projects = project_history
    if selected_project_obj:
        roadmap_projects = [item for item in project_history if item['project'].pk == selected_project_obj.pk]
    context = {
        'requests': requests,
        'payments': payments,
        'project_history': project_history,
        'roadmap_projects': roadmap_projects,
        'projects': projects,
        'selected_project': selected_project,
        'stats': {
            'requests': requests.count(),
            'pending': requests.filter(status=ClientRequest.STATUS_PENDING).count(),
            'in_progress': requests.filter(status=ClientRequest.STATUS_IN_PROGRESS).count(),
            'completed': requests.filter(status=ClientRequest.STATUS_COMPLETED).count(),
            'requested_amount': requested,
            'paid_amount': paid,
            'remaining_amount': requested - paid,
        },
        'active_nav': 'dashboard',
    }
    return render(request, 'core/client_dashboard.html', context)


@login_required
def client_request_new(request):
    if is_admin_user(request.user):
        return redirect('admin_dashboard')

    form = ClientRequestForm(request.POST or None, user=request.user)
    request_history = request.user.client_requests.select_related('project').all()
    history_project = request.GET.get('history_project', '')
    history_sort = request.GET.get('history_sort', 'recent')
    history_from = request.GET.get('history_from', '')
    history_to = request.GET.get('history_to', '')
    if history_project:
        request_history = request_history.filter(project_id=history_project)
    if history_from:
        request_history = request_history.filter(created_at__date__gte=history_from)
    if history_to:
        request_history = request_history.filter(created_at__date__lte=history_to)
    if history_sort == 'oldest':
        request_history = request_history.order_by('created_at')
    else:
        request_history = request_history.order_by('-created_at')
    if request.method == 'POST' and form.is_valid():
        client_request = form.save(commit=False)
        client_request.client = request.user
        client_request.save()
        for upload in request.FILES.getlist('client_files'):
            RequestAttachment.objects.create(
                request=client_request,
                uploaded_by=request.user,
                file=upload,
            )
        messages.success(request, 'Your request has been posted.')
        return redirect('client_dashboard')

    return render(
        request,
        'core/client_request_form.html',
        {
            'request_form': form,
            'history_requests': request_history,
            'history_projects': request.user.projects.all(),
            'selected_history_project': history_project,
            'selected_history_sort': history_sort,
            'selected_history_from': history_from,
            'selected_history_to': history_to,
            'active_nav': 'new_request',
        },
    )


@login_required
def client_payments(request):
    if is_admin_user(request.user):
        return redirect('admin_dashboard')

    payments = request.user.payments.select_related('request', 'project').all()
    ledger_payments = payments.filter(paid_amount__gt=0)
    proofs = request.user.payment_proofs.select_related('payment', 'payment__project').all()
    form = ClientPaymentProofForm(request.POST or None, request.FILES or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        proof = form.save(commit=False)
        proof.client = request.user
        proof.save()
        messages.success(request, 'Payment proof uploaded for admin review.')
        return redirect('client_payments')
    payment_balance_map = {
        str(payment.pk): str(payment.remaining_amount)
        for payment in payments
    }
    # handle ledger PDF download for client
    if request.GET.get('download') == 'ledger':
        from io import BytesIO

        def generate_ledger_pdf(payments_qs, title):
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
            styles = getSampleStyleSheet()
            elems = [Paragraph(title, styles['Title']), Spacer(1, 12)]
            data = [['Date', 'Project', 'Purpose', 'Paid', 'Balance', 'Status']]
            for p in payments_qs:
                date_str = p.date.strftime('%d %b %Y') if getattr(p, 'date', None) else ''
                proj = p.project.name if getattr(p, 'project', None) else 'No project'
                purpose = p.request.title if getattr(p, 'request', None) else 'General payment'
                data.append([date_str, proj, purpose, f'Rs. {p.paid_amount}', f'Rs. {p.remaining_amount}', p.get_status_display()])
            table = Table(data, colWidths=[70,120,160,70,70,70])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (3, 1), (4, -1), 'RIGHT'),
            ]))
            elems.append(table)
            doc.build(elems)
            pdf = buffer.getvalue()
            buffer.close()
            return pdf

        pdf_bytes = generate_ledger_pdf(ledger_payments, f"{request.user.get_full_name() or request.user.username} - Ledger")
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="ledger_{request.user.pk}.pdf"'
        return response
    return render(
        request,
        'core/client_payments.html',
        {
            'payments': payments,
            'ledger_payments': ledger_payments,
            'proofs': proofs,
            'form': form,
            'payment_balance_map': payment_balance_map,
            'active_nav': 'payments',
        },
    )
@login_required
@user_passes_test(is_admin_user, login_url='client_dashboard')
def admin_send_manager_message(request, pk):
    manager = get_object_or_404(User, pk=pk, is_staff=True, is_superuser=False)
    if request.method == 'POST':
        title = request.POST.get('title')
        message = request.POST.get('message')
        if title and message:
            ManagerQuery.objects.create(manager=manager, title=title, message=message)
            log_event(request.user, 'Message sent', f'Sent admin request to manager {manager.username}.')
            messages.success(request, f'Message sent to {manager.get_full_name() or manager.username}.')
        else:
            messages.error(request, 'Please provide both a title and message.')
    return redirect('admin_managers')


@login_required
@user_passes_test(lambda u: u.is_staff and not u.is_superuser, login_url='client_dashboard')
def manager_admin_requests(request):
    queries = request.user.admin_queries.all()
    # Mark as read
    queries.filter(status=ManagerQuery.STATUS_SENT).update(status=ManagerQuery.STATUS_READ)
    return render(
        request,
        'core/manager_admin_requests.html',
        {'queries': queries, 'active_nav': 'admin_requests'}
    )
