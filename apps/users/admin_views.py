import subprocess
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q, Avg
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from apps.users.models import User
from apps.verification.models import KYCSubmission, VerificationLog
from apps.authentication.models import APIKey, APIKeyLog
from apps.core.models import SystemSettings

@staff_member_required
def admin_dashboard(request):
    """Admin dashboard"""
    
    # Stats
    total_users = User.objects.count()
    active_today = User.objects.filter(last_login__date=timezone.now().date()).count()
    
    total_submissions = KYCSubmission.objects.count()
    pending_count = KYCSubmission.objects.filter(status='pending').count()
    approved_count = KYCSubmission.objects.filter(status='approved').count()
    rejected_count = KYCSubmission.objects.filter(status='rejected').count()
    flagged_count = KYCSubmission.objects.filter(status='flagged').count()
    
    # Today's stats
    today = timezone.now().date()
    today_submissions = KYCSubmission.objects.filter(created_at__date=today).count()
    today_approved = KYCSubmission.objects.filter(reviewed_at__date=today, status='approved').count()
    
    # Recent submissions
    recent_submissions = KYCSubmission.objects.select_related('reviewed_by').order_by('-created_at')[:10]
    
    # API usage
    total_api_calls = APIKeyLog.objects.count()
    api_calls_today = APIKeyLog.objects.filter(timestamp__date=today).count()
    active_keys = APIKey.objects.filter(is_active=True).count()
    
    context = {
        'total_users': total_users,
        'active_today': active_today,
        'total_submissions': total_submissions,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'flagged_count': flagged_count,
        'today_submissions': today_submissions,
        'today_approved': today_approved,
        'recent_submissions': recent_submissions,
        'total_api_calls': total_api_calls,
        'api_calls_today': api_calls_today,
        'active_keys': active_keys,
    }
    
    return render(request, 'admin/dashboard.html', context)

@staff_member_required
def kyc_list(request):
    """List all KYC submissions with filters"""
    status_filter = request.GET.get('status', 'all')
    
    submissions = KYCSubmission.objects.select_related('reviewed_by').order_by('-created_at')
    
    if status_filter != 'all':
        submissions = submissions.filter(status=status_filter)
    
    context = {
        'submissions': submissions,
        'status_filter': status_filter,
        'pending_count': KYCSubmission.objects.filter(status='pending').count(),
        'flagged_count': KYCSubmission.objects.filter(status='flagged').count(),
    }
    
    return render(request, 'admin/kyc_list.html', context)

@staff_member_required
def kyc_review(request, submission_id):
    """Review KYC submission"""
    submission = get_object_or_404(KYCSubmission, id=submission_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            submission.status = 'approved'
            submission.reviewed_by = request.user
            submission.reviewed_at = timezone.now()
            submission.save()
            
            VerificationLog.objects.create(
                submission=submission,
                action='manual_approved',
                performed_by=request.user.username,
                details={'reviewer': request.user.username}
            )
            
            messages.success(request, 'KYC approved successfully')
            
        elif action == 'reject':
            reason = request.POST.get('rejection_reason')
            submission.status = 'rejected'
            submission.rejection_reason = reason
            submission.reviewed_by = request.user
            submission.reviewed_at = timezone.now()
            submission.save()
            
            VerificationLog.objects.create(
                submission=submission,
                action='manual_rejected',
                performed_by=request.user.username,
                details={'reason': reason, 'reviewer': request.user.username}
            )
            
            messages.success(request, 'KYC rejected')
        
        return redirect('admin:kyc-list')
    
    return render(request, 'admin/kyc_review.html', {'submission': submission})

@staff_member_required
def user_list(request):
    """List all users"""
    users = User.objects.annotate(
        submission_count=Count('kyc_submissions'),
        api_calls=Count('api_key__logs')
    ).order_by('-date_joined')
    
    return render(request, 'admin/users.html', {'users': users})

@staff_member_required
def revoke_user_key(request, user_id):
    """Revoke a user's API key"""
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        APIKey.objects.filter(user=user).delete()
        messages.success(request, f'API key for {user.username} revoked successfully')
    return redirect('admin:user-detail', user_id=user_id)

@staff_member_required
def user_detail(request, user_id):
    """View and edit user details"""
    target_user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        try:
            target_user.daily_request_limit = int(request.POST.get('daily_limit', target_user.daily_request_limit) or 1000)
        except (TypeError, ValueError):
            target_user.daily_request_limit = 1000
        try:
            target_user.monthly_request_limit = int(request.POST.get('monthly_limit', target_user.monthly_request_limit) or 30000)
        except (TypeError, ValueError):
            target_user.monthly_request_limit = 30000
        target_user.is_active = request.POST.get('is_active') == 'on'
        target_user.is_verified = request.POST.get('is_verified') == 'on'
        target_user.save()
        messages.success(request, 'User updated successfully')
        return redirect('admin:user-detail', user_id=target_user.id)
    
    # Submissions: by submitted_by (Django user) or fallback user_id/email
    submissions = KYCSubmission.objects.filter(submitted_by=target_user).order_by('-created_at')
    if not submissions.exists():
        submissions = KYCSubmission.objects.filter(
            Q(user_id=str(target_user.id)) | Q(user_email=target_user.email)
        ).order_by('-created_at')
    
    api_key = None
    api_logs = []
    try:
        api_key = target_user.api_key
        api_logs = APIKeyLog.objects.filter(api_key=api_key).order_by('-timestamp')[:50]
    except APIKey.DoesNotExist:
        pass
    
    context = {
        'target_user': target_user,
        'submissions': submissions,
        'api_key': api_key,
        'api_logs': api_logs,
    }
    
    return render(request, 'admin/user_detail.html', context)

@staff_member_required
def admin_settings(request):
    """Admin settings - load/save SystemSettings."""
    settings_obj = SystemSettings.get_settings()
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type', '')
        apply_to_all = request.POST.get('apply_to_all') == 'on'
        
        if form_type == 'rate_limits':
            try:
                settings_obj.default_daily_limit = int(request.POST.get('default_daily_limit', settings_obj.default_daily_limit) or 1000)
                settings_obj.default_monthly_limit = int(request.POST.get('default_monthly_limit', settings_obj.default_monthly_limit) or 30000)
            except (TypeError, ValueError):
                pass
            settings_obj.save()
            if apply_to_all:
                User.objects.update(
                    daily_request_limit=settings_obj.default_daily_limit,
                    monthly_request_limit=settings_obj.default_monthly_limit,
                )
            messages.success(request, 'Rate limits saved.' + (' Applied to all users.' if apply_to_all else ''))
            
        elif form_type == 'api_settings':
            try:
                settings_obj.key_expiry_days = int(request.POST.get('key_expiry_days', settings_obj.key_expiry_days) or 365)
            except (TypeError, ValueError):
                pass
            settings_obj.require_approval_new_keys = request.POST.get('require_approval_new_keys') == 'on'
            settings_obj.auto_approve_high_confidence = request.POST.get('auto_approve_high_confidence') == 'on'
            settings_obj.save()
            messages.success(request, 'API settings saved.')
            
        elif form_type == 'kyc_settings':
            try:
                settings_obj.approve_threshold = max(0, min(100, int(request.POST.get('approve_threshold', settings_obj.approve_threshold) or 85)))
                settings_obj.reject_threshold = max(0, min(100, int(request.POST.get('reject_threshold', settings_obj.reject_threshold) or 40)))
                settings_obj.max_image_size_mb = float(request.POST.get('max_image_size', settings_obj.max_image_size_mb) or 5)
            except (TypeError, ValueError):
                pass
            settings_obj.allowed_image_formats = (request.POST.get('image_formats', settings_obj.allowed_image_formats) or 'jpg,jpeg,png').strip()
            settings_obj.save()
            messages.success(request, 'KYC settings saved.')
            
        elif form_type == 'security':
            try:
                settings_obj.session_timeout_minutes = int(request.POST.get('session_timeout', settings_obj.session_timeout_minutes) or 30)
            except (TypeError, ValueError):
                pass
            settings_obj.force_2fa_admin = request.POST.get('force_2fa') == 'on'
            settings_obj.ip_whitelist_enabled = request.POST.get('ip_whitelist') == 'on'
            settings_obj.save()
            messages.success(request, 'Security settings saved.')
            
        return redirect('admin:settings')
    
    today = timezone.now().date()
    total_api_calls = APIKeyLog.objects.count()
    unique_users = APIKeyLog.objects.values('api_key__user').distinct().count()
    avg_response = APIKeyLog.objects.aggregate(Avg('response_time'))['response_time__avg'] or 0
    
    context = {
        'settings': settings_obj,
        'total_api_calls': total_api_calls,
        'unique_users': unique_users,
        'avg_response': avg_response,
    }
    
    return render(request, 'admin/settings.html', context)


# Blocked patterns for terminal (dangerous commands)
TERMINAL_BLOCKED = re.compile(
    r'(\brm\s+-[rf]+\s+/|\b:\(\)\s*\{|>\s*/dev/sd|mkfs\.|dd\s+if=|\bchmod\s+[0-7]+\s+/|/etc/shadow|/etc/passwd\s*$)',
    re.IGNORECASE
)
TERMINAL_TIMEOUT = 30


@staff_member_required
def terminal_view(request):
    """Admin terminal page - container shell access."""
    pending_count = KYCSubmission.objects.filter(status='pending').count()
    return render(request, 'admin/terminal.html', {'pending_count': pending_count})


@staff_member_required
@require_http_methods(['POST'])
def terminal_run_command(request):
    """Run a command in the container and return stdout/stderr (JSON)."""
    cmd = (request.POST.get('command') or request.body.decode('utf-8', errors='ignore')).strip()
    if not cmd:
        return JsonResponse({'ok': False, 'stdout': '', 'stderr': 'No command provided.', 'returncode': -1})
    if TERMINAL_BLOCKED.search(cmd):
        return JsonResponse({'ok': False, 'stdout': '', 'stderr': 'Command not allowed for security.', 'returncode': -1})
    try:
        result = subprocess.run(
            ['sh', '-c', cmd],
            capture_output=True,
            text=True,
            timeout=TERMINAL_TIMEOUT,
            cwd='/app',
        )
        return JsonResponse({
            'ok': result.returncode == 0,
            'stdout': result.stdout or '',
            'stderr': result.stderr or '',
            'returncode': result.returncode,
        })
    except subprocess.TimeoutExpired:
        return JsonResponse({
            'ok': False,
            'stdout': '',
            'stderr': f'Command timed out after {TERMINAL_TIMEOUT}s.',
            'returncode': -1,
        })
    except Exception as e:
        return JsonResponse({
            'ok': False,
            'stdout': '',
            'stderr': str(e),
            'returncode': -1,
        })