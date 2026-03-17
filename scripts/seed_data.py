"""
Seed data: ~10 users (5 with API key, 5 without), ~20 KYC submissions, API logs.
  --clear  Remove all non-staff users and all submissions/logs (keeps is_staff=True).

Run from kyc_hybrid_service:  python scripts/seed_data.py  [--clear]
"""
import os
import sys
import random
from datetime import timedelta

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.management import call_command
from apps.authentication.models import APIKey, APIKeyLog
from apps.verification.models import KYCSubmission, KYCDocument, VerificationLog
from apps.core.models import SystemSettings

User = get_user_model()

NUM_USERS = 10
NUM_USERS_WITHOUT_KEY = 5   # of the 10, this many will have no API key
TOTAL_KYC_SUBMISSIONS = 20
API_LOGS_PER_USER_MIN = 1
API_LOGS_PER_USER_MAX = 8

FIRST_NAMES = [
    'Abebe', 'Tigist', 'Dawit', 'Sara', 'Yonas', 'Meron', 'Ephrem', 'Hanna',
    'Solomon', 'Bethlehem', 'Daniel', 'Marta', 'Samuel', 'Rahel', 'Michael',
]
LAST_NAMES = [
    'Tesfaye', 'Kebede', 'Abebe', 'Hailu', 'Tadesse', 'Girma', 'Alemu', 'Desta',
    'Gebre', 'Assefa', 'Mekonnen', 'Bekele', 'Worku', 'Negash', 'Solomon',
]
ID_TYPES = ['national_id', 'passport', 'drivers_license', 'kebele']
STATUSES = ['pending', 'processing', 'approved', 'rejected', 'flagged']
ENDPOINTS = ['/api/v1/kyc/submit/', '/api/v1/kyc/status/']
METHODS = ['POST', 'GET']


def log(msg):
    print(f"  [seed] {msg}")


def random_email(name):
    base = name.lower().replace(' ', '.')
    return f"{base}{random.randint(1, 999)}@example.com"


def random_ip():
    return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


def run_clear():
    """Remove all non-staff users and all KYC/API data. Keep is_staff=True users."""
    log("--clear: cleaning data (keeping staff users)...")
    from apps.verification.models import KYCDocument
    # Delete in FK order
    VerificationLog.objects.all().delete()
    log("  Deleted all VerificationLog")
    KYCDocument.objects.all().delete()
    log("  Deleted all KYCDocument")
    KYCSubmission.objects.all().delete()
    log("  Deleted all KYCSubmission")
    APIKeyLog.objects.all().delete()
    log("  Deleted all APIKeyLog")
    APIKey.objects.all().delete()
    log("  Deleted all APIKey")
    deleted_users = User.objects.filter(is_staff=False).delete()
    log(f"  Deleted {deleted_users[0]} non-staff users")
    log("--clear done.")


def main():
    if '--clear' in sys.argv:
        run_clear()
        if len(sys.argv) == 2:
            return
        # continue to seed after clear if more args

    log("Seeding data...")
    # Ensure default admin exists (same as create_default_admin)
    if not User.objects.filter(is_superuser=True).exists():
        call_command("create_default_admin", "--noinput")
        log("Created default admin (admin / admin@kyc.local).")
    settings_obj = SystemSettings.get_settings()

    # ----- 1. Create 10 users: 5 with API key, 5 without -----
    users_created = 0
    users_with_key = []
    users_without_key = []
    for i in range(NUM_USERS):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        username = f"seed_user_{i+1}_{first.lower()}"
        email = random_email(f"{first} {last}")
        if User.objects.filter(username=username).exists():
            u = User.objects.get(username=username)
            try:
                u.api_key
                users_with_key.append(u)
            except APIKey.DoesNotExist:
                users_without_key.append(u)
            continue
        user = User.objects.create_user(
            username=username,
            email=email,
            password='seedpass123',
            first_name=first,
            last_name=last,
            daily_request_limit=settings_obj.default_daily_limit,
            monthly_request_limit=settings_obj.default_monthly_limit,
        )
        users_created += 1
        log(f"Created user {users_created}/{NUM_USERS}: {username}")
        give_key = (i >= NUM_USERS_WITHOUT_KEY)
        if give_key:
            APIKey.objects.create(
                user=user,
                name=f"Key for {user.email}",
                expires_at=timezone.now() + timedelta(days=365),
            )
            user.refresh_from_db()
            users_with_key.append(user)
            log(f"  -> API key created for {username}")
        else:
            users_without_key.append(user)
            log(f"  -> no API key (as requested)")

    all_seed_users = users_with_key + users_without_key
    if not all_seed_users:
        all_seed_users = list(User.objects.filter(is_staff=False))
    if not users_with_key:
        users_with_key = list(User.objects.filter(api_key__isnull=False).select_related('api_key'))
    log(f"Users with API key: {len(users_with_key)}, without: {len(users_without_key)}")

    # ----- 2. API key logs (only for users that have a key) -----
    logs_created = 0
    log_ids = []
    for user in users_with_key:
        try:
            api_key = user.api_key
        except APIKey.DoesNotExist:
            continue
        n_logs = random.randint(API_LOGS_PER_USER_MIN, API_LOGS_PER_USER_MAX)
        for j in range(n_logs):
            l = APIKeyLog.objects.create(
                api_key=api_key,
                endpoint=random.choice(ENDPOINTS),
                method=random.choice(METHODS),
                status_code=random.choice([200, 200, 201, 400, 429, 500]),
                ip_address=random_ip(),
                user_agent="SeedScript/1.0",
                response_time=round(random.uniform(0.1, 2.5), 2),
            )
            log_ids.append((l.pk, random.randint(0, 14)))
            logs_created += 1
        log(f"Created {n_logs} API log entries for {user.username}")
    for log_id, days_ago in log_ids[: max(1, len(log_ids) // 2)]:
        past = timezone.now() - timedelta(days=days_ago, minutes=random.randint(0, 60 * 24))
        APIKeyLog.objects.filter(pk=log_id).update(timestamp=past)
    log(f"Total APIKeyLog entries: {logs_created}")

    # ----- 3. ~20 KYC submissions (spread across users; submitted_by can be any seed user) -----
    kyc_created = 0
    for i in range(TOTAL_KYC_SUBMISSIONS):
        submitter = random.choice(all_seed_users) if all_seed_users else None
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        user_id = f"app_{random.randint(10000, 99999)}"
        user_email = random_email(f"{first} {last}")
        user_full_name = f"{first} {last}"
        id_type = random.choice(ID_TYPES)
        id_number = ''.join(random.choices('0123456789', k=random.randint(10, 14)))
        status = random.choice(STATUSES)
        confidence = round(random.uniform(0.2, 0.95), 4)
        created_at = timezone.now() - timedelta(days=random.randint(0, 30))

        sub = KYCSubmission(
            user_id=user_id,
            user_email=user_email,
            user_full_name=user_full_name,
            submitted_by=submitter,
            id_type=id_type,
            id_number=id_number,
            status=status,
            confidence_score=confidence,
            verification_data={
                'overall_confidence': confidence,
                'checks': {'face_match': {'score': round(random.uniform(0.5, 0.95), 2)}},
            },
            ip_address=random_ip(),
        )
        sub.save()
        KYCSubmission.objects.filter(pk=sub.pk).update(created_at=created_at, submitted_at=created_at)
        if status in ('approved', 'rejected') and random.random() > 0.5:
            KYCSubmission.objects.filter(pk=sub.pk).update(
                processed_at=created_at + timedelta(seconds=random.randint(5, 60))
            )
        VerificationLog.objects.create(
            submission=sub,
            action=random.choice(['submitted', 'auto_approved', 'auto_rejected', 'flagged']),
            performed_by='system' if random.random() > 0.3 else sub.user_id,
            details={'seed': True},
            ip_address=sub.ip_address,
        )
        kyc_created += 1
        log(f"Created KYC submission {kyc_created}/{TOTAL_KYC_SUBMISSIONS}: {user_full_name} ({status})")
    log(f"Total KYC submissions: {kyc_created}")

    log("Done.")


if __name__ == '__main__':
    main()
