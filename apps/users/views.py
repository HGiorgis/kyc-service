from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
from django.db import models
from django.db.models.functions import TruncDate
from django.db.models import Count
from .forms import (
    CustomUserCreationForm, CustomAuthenticationForm, 
    UserProfileForm, ChangePasswordForm
)
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from apps.authentication.models import APIKey, APIKeyLog
from apps.verification.models import KYCSubmission, KYCDocument, VerificationLog
from apps.core.models import SystemSettings
from datetime import timedelta
import json
import time


def landing_page_view(request):
    """Public landing page at / ."""
    return render(request, 'landing.html')


def register_view(request):
    """User registration"""
    if request.user.is_authenticated:
        return redirect('admin:dashboard' if request.user.is_staff else 'user:dashboard')
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            try:
                s = SystemSettings.get_settings()
                user.daily_request_limit = s.default_daily_limit
                user.monthly_request_limit = s.default_monthly_limit
                user.save(update_fields=['daily_request_limit', 'monthly_request_limit'])
            except Exception:
                pass
            login(request, user)
            messages.success(request, 'Registration successful! Welcome to KYC Service.')
            return redirect('user:dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'auth/register.html', {'form': form})

def login_view(request):
    """User login"""
    if request.user.is_authenticated:
        return redirect('admin:dashboard' if request.user.is_staff else 'user:dashboard')
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                
                # Redirect based on role
                if user.is_staff:
                    return redirect('admin:dashboard')
                return redirect('user:dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'auth/login.html', {'form': form})

@login_required
def logout_view(request):
    """User logout"""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('auth:login')

@login_required
def dashboard_view(request):
    """User dashboard"""
    try:
        api_key = request.user.api_key
    except APIKey.DoesNotExist:
        api_key = None
    
    # Get recent API usage
    recent_logs = []
    if api_key:
        recent_logs = APIKeyLog.objects.filter(
            api_key=api_key
        ).order_by('-timestamp')[:10]
    
    # Calculate usage stats
    today = timezone.now().date()
    month_start = timezone.now().replace(day=1)
    
    total_calls = APIKeyLog.objects.filter(api_key=api_key).count() if api_key else 0
    today_calls = APIKeyLog.objects.filter(
        api_key=api_key,
        timestamp__date=today
    ).count() if api_key else 0
    
    month_calls = APIKeyLog.objects.filter(
        api_key=api_key,
        timestamp__gte=month_start
    ).count() if api_key else 0
    
    stats = {
        'total_calls': total_calls,
        'calls_today': today_calls,
        'calls_this_month': month_calls,
        'daily_limit': request.user.daily_request_limit,
        'monthly_limit': request.user.monthly_request_limit,
        'last_used': api_key.last_used_at if api_key else None,
        'expires_in': (api_key.expires_at - timezone.now()).days if api_key and api_key.expires_at else None,
    }
    
    new_api_key = request.session.pop('new_api_key', None)
    context = {
        'api_key': api_key,
        'recent_logs': recent_logs,
        'stats': stats,
        'new_api_key': new_api_key,
    }
    return render(request, 'user/dashboard.html', context)

@login_required
def profile_view(request):
    """User profile settings"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('user:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    active_section = request.GET.get('section', 'account')
    return render(request, 'user/profile.html', {'form': form, 'active_section': active_section})

@login_required
def change_password(request):
    """Change password: GET redirects to profile#password; POST processes then redirects."""
    if request.method != 'POST':
        return redirect(reverse('user:profile') + '?section=password')
    form = ChangePasswordForm(request.POST)
    if form.is_valid():
        user = request.user
        if user.check_password(form.cleaned_data['current_password']):
            user.set_password(form.cleaned_data['new_password'])
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully.')
        else:
            messages.error(request, 'Current password is incorrect.')
    else:
        messages.error(request, 'Please fix the errors below.')
    return redirect(reverse('user:profile') + '?section=password')

@login_required
def usage_view(request):
    """API usage statistics with chart data"""
    try:
        api_key = request.user.api_key
    except APIKey.DoesNotExist:
        messages.warning(request, 'Generate an API key first')
        return redirect('user:dashboard')

    # Use api_key_id so we always match the key for this user (logs from API + test page)
    logs = APIKeyLog.objects.filter(api_key_id=api_key.id).order_by('-timestamp')
    total_calls = logs.count()
    success_calls = logs.filter(status_code__in=[200, 201]).count()
    failed_calls = total_calls - success_calls
    avg_response = 0
    if total_calls > 0:
        avg_response = logs.aggregate(models.Avg('response_time'))['response_time__avg'] or 0

    # Chart: last 14 days daily request counts (group by day)
    start_date = timezone.now().date() - timedelta(days=14)
    daily_qs = (
        logs.filter(timestamp__date__gte=start_date)
        .annotate(day=TruncDate('timestamp'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    day_counts = {}
    for row in daily_qs:
        day_val = row['day']
        key = day_val.isoformat() if hasattr(day_val, 'isoformat') else str(day_val)
        day_counts[key] = int(row['count'])
    chart_labels = []
    chart_values = []
    for i in range(14):
        d = start_date + timedelta(days=i)
        chart_labels.append(d.strftime('%b %d'))
        chart_values.append(day_counts.get(d.isoformat(), 0))

    today = timezone.now().date()
    month_start = timezone.now().replace(day=1)
    calls_today = logs.filter(timestamp__date=today).count()
    calls_this_month = logs.filter(timestamp__gte=month_start).count()

    context = {
        'logs': list(logs[:100]),
        'total_calls': total_calls,
        'success_calls': success_calls,
        'failed_calls': failed_calls,
        'avg_response': round(avg_response, 2),
        'chart_labels': chart_labels,
        'chart_values': chart_values,
        'chart_labels_json': json.dumps(chart_labels),
        'chart_values_json': json.dumps(chart_values),
        'daily_limit': request.user.daily_request_limit,
        'monthly_limit': request.user.monthly_request_limit,
        'calls_today': calls_today,
        'calls_this_month': calls_this_month,
    }
    return render(request, 'user/usage.html', context)

@login_required
def generate_api_key(request):
    """Generate new API key - show full key once in dashboard modal"""
    APIKey.objects.filter(user=request.user).delete()
    settings_obj = SystemSettings.get_settings()
    expires_at = timezone.now() + timedelta(days=settings_obj.key_expiry_days)
    api_key = APIKey.objects.create(
        user=request.user,
        name=f"API Key for {request.user.email}",
        expires_at=expires_at,
    )
    request.session['new_api_key'] = api_key.key
    messages.success(request, 'API key created. Copy it below — you won’t see it again.')
    return redirect('user:dashboard')

@login_required
def revoke_api_key(request):
    """Revoke current API key"""
    if request.method == 'POST':
        APIKey.objects.filter(user=request.user).delete()
        messages.success(request, 'API key revoked successfully')
    return redirect('user:dashboard')


def _log_test_page_call(request, api_key, status_code, response_time_sec):
    """Record test page submission as API usage. Skip record_usage() for 429 so limit stays enforced."""
    if not api_key:
        return
    try:
        ip = request.META.get('REMOTE_ADDR') or '0.0.0.0'
        APIKeyLog.objects.create(
            api_key_id=api_key.id,
            endpoint='/user/test/',
            method='POST',
            status_code=status_code,
            ip_address=ip,
            user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:500],
            response_time=response_time_sec,
        )
        if status_code != 429:
            api_key.record_usage()
    except Exception:
        pass


@login_required
def test_kyc_view(request):
    """Test KYC flow: upload images and run verification with user's API key."""
    try:
        api_key = request.user.api_key
    except APIKey.DoesNotExist:
        api_key = None
    if not api_key:
        messages.warning(request, 'Generate an API key first to use the test page.')
        return redirect('user:dashboard')

    result = None
    if request.method == 'POST':
        start_time = time.time()
        # 1. Check rate limit first — block if at or over limit (same as API)
        ok, msg = request.user.check_rate_limit()
        if not ok:
            messages.error(request, f'Rate limit exceeded: {msg}')
            _log_test_page_call(request, api_key, 429, time.time() - start_time)
        else:
            user_id = request.POST.get('user_id', '').strip() or f"test_{request.user.id}_{int(timezone.now().timestamp())}"
            user_email = request.POST.get('email', '').strip() or request.user.email
            user_name = request.POST.get('full_name', '').strip() or request.user.get_full_name() or request.user.username
            id_type = request.POST.get('id_type', 'national_id')
            id_number = request.POST.get('id_number', '').strip()
            id_front = request.FILES.get('id_front')
            id_back = request.FILES.get('id_back')
            selfie = request.FILES.get('selfie')

            if not all([id_front, id_back, selfie]):
                messages.error(request, 'Please upload all three images: ID front, ID back, and selfie.')
                _log_test_page_call(request, api_key, 400, time.time() - start_time)
            elif not id_number:
                messages.error(request, 'ID number is required.')
                _log_test_page_call(request, api_key, 400, time.time() - start_time)
            else:
                try:
                    from apps.api.views.kyc_views import _run_verification_in_background
                    submission = KYCSubmission.objects.create(
                        user_id=user_id,
                        user_email=user_email,
                        user_full_name=user_name,
                        id_type=id_type,
                        id_number=id_number,
                        status='processing',
                        ip_address=request.META.get('REMOTE_ADDR') or None,
                        user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:500],
                        submitted_by=request.user,
                    )
                    KYCDocument.objects.create(submission=submission, document_type='id_front', file=id_front)
                    KYCDocument.objects.create(submission=submission, document_type='id_back', file=id_back)
                    KYCDocument.objects.create(submission=submission, document_type='selfie', file=selfie)
                    VerificationLog.objects.create(
                        submission=submission, action='submitted', performed_by=user_id,
                        ip_address=request.META.get('REMOTE_ADDR') or None,
                        details={'id_type': id_type, 'source': 'test_page'},
                    )
                    _run_verification_in_background(submission.id)
                    _log_test_page_call(request, api_key, 200, time.time() - start_time)
                    # When client expects JSON (AJAX upload), return immediately so they see "in process" as soon as upload finishes
                    if request.accepts('application/json') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'submission_id': str(submission.id),
                            'in_process': True,
                            'message': 'Your documents have been received and are being verified. It may take a few minutes. Use "Check status" below when ready.',
                        })
                    messages.success(request, 'Documents received and in process. Use "Check status" below when ready.')
                    return redirect(reverse('user:test') + f'?submission_id={submission.id}')
                except MemoryError:
                    messages.error(request, 'Server ran out of memory. Please use smaller images (under 2MB each) and try again.')
                    result = {'status': 'error', 'flags': ['Out of memory'], 'overall_confidence': 0}
                    _log_test_page_call(request, api_key, 503, time.time() - start_time)
                except Exception as e:
                    messages.error(request, f'Test failed: {str(e)}')
                    result = {'status': 'error', 'flags': [str(e)], 'overall_confidence': 0}
                    _log_test_page_call(request, api_key, 500, time.time() - start_time)

    submission_id = request.GET.get('submission_id')
    context = {
        'api_key': api_key,
        'test_result': result,
        'submission_id': submission_id,
        'in_process': bool(submission_id and result is None),
    }
    return render(request, 'user/test.html', context)


@login_required
@require_GET
def test_kyc_status_view(request, submission_id):
    """Return JSON status for a submission (only if submitted by current user). For test page polling."""
    try:
        submission = KYCSubmission.objects.get(id=submission_id, submitted_by=request.user)
    except KYCSubmission.DoesNotExist:
        return JsonResponse({'error': 'Not found', 'status': 'not_found'}, status=404)
    payload = {
        'submission_id': str(submission.id),
        'status': submission.status,
        'confidence': submission.confidence_score,
        'processed_at': submission.processed_at.isoformat() if submission.processed_at else None,
        'rejection_reason': submission.rejection_reason,
    }
    if submission.status not in ('pending', 'processing') and submission.verification_data:
        payload['verification_data'] = submission.verification_data
    return JsonResponse(payload)