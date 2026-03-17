"""
Upload all files from local MEDIA_ROOT to the configured Backblaze B2 (S3-compatible) bucket.
Preserves directory structure and sets ACL to private for every uploaded file.
Run only when B2 env vars are set (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME, AWS_S3_ENDPOINT_URL).
"""
import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage

try:
    import boto3
    from botocore.client import Config
except ImportError:
    boto3 = None


class Command(BaseCommand):
    help = 'Upload all files from local media/ to Backblaze B2 bucket (private ACL). Preserves nested paths.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='List files that would be uploaded without uploading.',
        )
        parser.add_argument(
            '--verify',
            action='store_true',
            help='After upload, list objects in the bucket to confirm (requires boto3).',
        )

    def handle(self, *args, **options):
        backend = default_storage.__class__.__name__
        if 'S3' not in backend and 'boto' not in backend.lower():
            # Show which env vars Django sees (helps when using .env or system env)
            ak = os.environ.get('AWS_ACCESS_KEY_ID', '')
            sk = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
            bucket = os.environ.get('AWS_STORAGE_BUCKET_NAME', '')
            self.stderr.write(
                self.style.ERROR(
                    'Default storage is not S3/B2. Required env vars (must be set before Django loads):'
                )
            )
            self.stderr.write(
                f'  AWS_ACCESS_KEY_ID: {"set (" + str(len(ak)) + " chars)" if ak else "NOT SET"}'
            )
            self.stderr.write(
                f'  AWS_SECRET_ACCESS_KEY: {"set (" + str(len(sk)) + " chars)" if sk else "NOT SET"}'
            )
            self.stderr.write(
                f'  AWS_STORAGE_BUCKET_NAME: {"set (" + bucket + ")" if bucket else "NOT SET"}'
            )
            self.stderr.write(
                'If using a .env file, put it in the project root (same folder as manage.py) and use exact names above.'
            )
            return

        media_root = Path(settings.MEDIA_ROOT)
        if not media_root.exists():
            self.stdout.write(self.style.WARNING(f'MEDIA_ROOT does not exist: {media_root}'))
            return

        files = [p for p in media_root.rglob('*') if p.is_file()]
        if not files:
            self.stdout.write(self.style.WARNING('No files found under MEDIA_ROOT.'))
            return

        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(f'[DRY RUN] Would upload {len(files)} file(s):')
            for p in sorted(files):
                try:
                    rel = p.relative_to(media_root)
                    self.stdout.write(f'  {rel}')
                except ValueError:
                    pass
            return

        uploaded = 0
        errors = 0
        for path in sorted(files):
            try:
                rel = path.relative_to(media_root)
                name = str(rel).replace(os.sep, '/')
            except ValueError:
                continue
            try:
                with open(path, 'rb') as f:
                    default_storage.save(name, f)
                uploaded += 1
                self.stdout.write(f'  {name}')
            except Exception as e:
                errors += 1
                self.stderr.write(self.style.ERROR(f'  {name}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Uploaded {uploaded} file(s).'))
        if errors:
            self.stderr.write(self.style.ERROR(f'Errors: {errors}'))

        # Show where files went so you can confirm in B2 UI (bucket name must match)
        bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
        endpoint = getattr(settings, 'AWS_S3_ENDPOINT_URL', None)
        if bucket:
            self.stdout.write('')
            self.stdout.write(f'Bucket: {bucket}')
            self.stdout.write(f'Endpoint: {endpoint}')
            self.stdout.write('In B2 dashboard: open the bucket named exactly above to see files (e.g. under kyc/).')

        if options.get('verify') and boto3 and bucket and uploaded:
            self._verify_bucket_list()

    def _verify_bucket_list(self):
        """List objects in the configured bucket to confirm uploads."""
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        endpoint = getattr(settings, 'AWS_S3_ENDPOINT_URL', None)
        region = getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-001')
        # B2 S3-compatible endpoint: use path-style or virtual-hosted; boto3 needs endpoint_url and region
        client = boto3.client(
            's3',
            endpoint_url=endpoint,
            region_name=region,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4'),
        )
        try:
            paginator = client.get_paginator('list_objects_v2')
            count = 0
            self.stdout.write('')
            self.stdout.write('Objects in bucket (--verify):')
            for page in paginator.paginate(Bucket=bucket):
                for obj in page.get('Contents') or []:
                    count += 1
                    self.stdout.write(f"  {obj['Key']}  ({obj.get('Size', 0)} bytes)")
            if count == 0:
                self.stdout.write(self.style.WARNING('  (no objects listed — check bucket name and endpoint)'))
            else:
                self.stdout.write(self.style.SUCCESS(f'  Total: {count} object(s).'))
        except Exception as e:
            err = str(e).strip()
            if 'AccessDenied' in err or 'not entitled' in err:
                self.stdout.write(
                    self.style.WARNING(
                        'List failed: your B2 Application Key has write but not list permission. '
                        'Upload succeeded. To use --verify, add "listFiles" (and readFiles) to the key in B2.'
                    )
                )
            else:
                self.stderr.write(self.style.ERROR(f'Verify list failed: {e}'))
