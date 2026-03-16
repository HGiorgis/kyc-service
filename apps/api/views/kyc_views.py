# apps/api/views/kyc_views.py
import time
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from apps.api.authentication import APIKeyAuthentication
from apps.verification.models import KYCSubmission, KYCDocument, VerificationLog
from apps.authentication.models import APIKeyLog
from apps.core.models import SystemSettings
from apps.core.services.verifier import KYCVerifier


def _log_api_call(request, api_key, endpoint, method, status_code, response_time_sec):
    """Create APIKeyLog entry for this request so Usage page shows real data."""
    if not api_key:
        return
    ip = request.META.get('REMOTE_ADDR') or '0.0.0.0'
    try:
        APIKeyLog.objects.create(
            api_key_id=api_key.id,
            endpoint=endpoint or '/api/v1/kyc/submit/',
            method=method or 'POST',
            status_code=status_code,
            ip_address=ip,
            user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:500],
            response_time=response_time_sec,
        )
    except Exception:
        pass


def _check_image_formats(files, allowed_formats):
    """Check that each file's extension is in allowed_formats. Returns (ok, error_message)."""
    allowed = set(f.strip().lower() for f in (allowed_formats or '').split(',') if f.strip())
    allowed.add('jpg')
    allowed.add('jpeg')
    for name, f in (files or []):
        if not f:
            continue
        fname = getattr(f, 'name', name) or name
        ext = (fname.split('.')[-1] or '').lower()
        if ext not in allowed:
            return False, f"File '{fname}' has disallowed format. Allowed: {', '.join(sorted(allowed))}"
    return True, None


class KYCSubmitView(APIView):
    """Submit KYC documents for verification"""
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        start_time = time.time()
        user = request.user
        api_key = request.auth
        endpoint = request.path or '/api/v1/kyc/submit/'

        try:
            # 1. Check rate limit first — before any other work
            ok, msg = user.check_rate_limit()
            if not ok:
                _log_api_call(request, api_key, endpoint, 'POST', 429, time.time() - start_time)
                return Response({
                    'error': msg,
                    'limit_reached': True,
                    'daily_limit': user.daily_request_limit,
                    'monthly_limit': user.monthly_request_limit,
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            api_key.record_usage()

            # Allowed image formats (system settings)
            settings_obj = SystemSettings.get_settings()
            allowed = settings_obj.allowed_image_formats
            files_to_check = [
                ('id_front', request.FILES.get('id_front')),
                ('id_back', request.FILES.get('id_back')),
                ('selfie', request.FILES.get('selfie')),
            ]
            ok, err = _check_image_formats(files_to_check, allowed)
            if not ok:
                resp = Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)
                _log_api_call(request, api_key, endpoint, 'POST', 400, time.time() - start_time)
                return resp

            user_id = request.data.get('user_id')
            user_email = request.data.get('email')
            user_name = request.data.get('full_name')
            id_type = request.data.get('id_type')
            id_number = request.data.get('id_number')
            id_front = request.FILES.get('id_front')
            id_back = request.FILES.get('id_back')
            selfie = request.FILES.get('selfie')

            if not all([user_id, user_email, user_name, id_type, id_number, id_front, id_back, selfie]):
                resp = Response({
                    'error': 'Missing required fields',
                    'required': ['user_id', 'email', 'full_name', 'id_type', 'id_number', 'id_front', 'id_back', 'selfie']
                }, status=status.HTTP_400_BAD_REQUEST)
                _log_api_call(request, api_key, endpoint, 'POST', 400, time.time() - start_time)
                return resp

            existing = KYCSubmission.objects.filter(
                user_id=user_id,
                status__in=['pending', 'processing', 'flagged']
            ).first()
            if existing:
                resp = Response({
                    'error': 'User already has pending KYC submission',
                    'submission_id': str(existing.id),
                    'status': existing.status
                }, status=status.HTTP_400_BAD_REQUEST)
                _log_api_call(request, api_key, endpoint, 'POST', 400, time.time() - start_time)
                return resp

            submission = KYCSubmission.objects.create(
                user_id=user_id,
                user_email=user_email,
                user_full_name=user_name,
                id_type=id_type,
                id_number=id_number,
                status='processing',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                submitted_by=user,
            )

            KYCDocument.objects.create(submission=submission, document_type='id_front', file=id_front)
            KYCDocument.objects.create(submission=submission, document_type='id_back', file=id_back)
            KYCDocument.objects.create(submission=submission, document_type='selfie', file=selfie)

            VerificationLog.objects.create(
                submission=submission,
                action='submitted',
                performed_by=user_id,
                ip_address=request.META.get('REMOTE_ADDR'),
                details={'id_type': id_type, 'api_key': api_key.key_preview}
            )

            verifier = KYCVerifier()
            result = verifier.verify_submission(submission)
            submission.verification_data = result
            submission.confidence_score = result.get('overall_confidence', 0)
            if result['status'] == 'approved':
                submission.status = 'approved'
            elif result['status'] == 'rejected':
                submission.status = 'rejected'
            else:
                submission.status = 'flagged'
            submission.processed_at = timezone.now()
            submission.save()

            log_action = {'approved': 'auto_approved', 'rejected': 'auto_rejected', 'flagged': 'flagged'}.get(result['status'], 'flagged')
            VerificationLog.objects.create(
                submission=submission,
                action=log_action,
                performed_by='system',
                details=result
            )

            _log_api_call(request, api_key, endpoint, 'POST', 201, time.time() - start_time)
            return Response({
                'submission_id': str(submission.id),
                'status': submission.status,
                'confidence': submission.confidence_score,
                'flags': result.get('flags', []),
                'message': f'KYC verification {submission.status}'
            }, status=status.HTTP_201_CREATED)

        except MemoryError:
            _log_api_call(request, api_key, endpoint, 'POST', 503, time.time() - start_time)
            return Response({
                'error': 'Server ran out of memory. Please try again with smaller images (e.g. under 2MB each).',
                'code': 'out_of_memory',
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except (SystemExit, OSError) as e:
            _log_api_call(request, api_key, endpoint, 'POST', 503, time.time() - start_time)
            return Response({
                'error': 'Verification could not complete. Please retry with smaller images.',
                'code': 'service_unavailable',
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            import traceback
            traceback.print_exc()
            _log_api_call(request, api_key, endpoint, 'POST', 500, time.time() - start_time)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class KYCStatusView(APIView):
    """Get KYC verification status"""
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        start_time = time.time()
        user = request.user
        api_key = request.auth
        endpoint = (request.path or '').rstrip('/') or '/api/v1/kyc/status/'

        try:
            # 1. Check rate limit first — before any other work
            ok, msg = user.check_rate_limit()
            if not ok:
                _log_api_call(request, api_key, endpoint, 'GET', 429, time.time() - start_time)
                return Response({
                    'error': msg,
                    'limit_reached': True,
                    'daily_limit': user.daily_request_limit,
                    'monthly_limit': user.monthly_request_limit,
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            api_key.record_usage()

            submission = KYCSubmission.objects.filter(user_id=user_id).order_by('-created_at').first()
            if not submission:
                resp = Response({
                    'user_id': user_id,
                    'status': 'not_found',
                    'message': 'No KYC submission found'
                }, status=status.HTTP_200_OK)
                _log_api_call(request, api_key, endpoint, 'GET', 200, time.time() - start_time)
                return resp

            _log_api_call(request, api_key, endpoint, 'GET', 200, time.time() - start_time)
            return Response({
                'user_id': user_id,
                'submission_id': str(submission.id),
                'status': submission.status,
                'confidence': submission.confidence_score,
                'submitted_at': submission.submitted_at,
                'processed_at': submission.processed_at,
                'reviewed_at': submission.reviewed_at,
                'rejection_reason': submission.rejection_reason
            })

        except Exception as e:
            _log_api_call(request, api_key, endpoint, 'GET', 500, time.time() - start_time)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
