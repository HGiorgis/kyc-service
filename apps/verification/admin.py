from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import KYCSubmission, KYCDocument, VerificationLog


class KYCDocumentInline(admin.TabularInline):
    model = KYCDocument
    extra = 0
    readonly_fields = ('document_preview', 'document_type', 'file', 'thumbnail', 'uploaded_at')
    fields = ('document_type', 'document_preview', 'file', 'thumbnail', 'uploaded_at')

    def document_preview(self, obj):
        if not obj or not obj.file:
            return mark_safe('<span class="quiet">—</span>')
        try:
            url = obj.file.url
        except Exception:
            return mark_safe('<span class="quiet">(unavailable)</span>')
        return format_html(
            '<a href="{}" target="_blank" rel="noopener"><img src="{}" alt="{}" style="max-height:80px;max-width:120px;object-fit:contain;" /></a>',
            url, url, obj.document_type
        )

    document_preview.short_description = 'Preview'


@admin.register(KYCSubmission)
class KYCSubmissionAdmin(admin.ModelAdmin):
    list_display = ('user_full_name', 'user_id', 'id_type', 'status', 'confidence_score', 'created_at')
    list_filter = ('status', 'id_type')
    search_fields = ('user_full_name', 'user_id', 'user_email', 'id_number')
    readonly_fields = ('id', 'created_at', 'updated_at', 'submitted_at', 'processed_at')
    inlines = [KYCDocumentInline]


@admin.register(KYCDocument)
class KYCDocumentAdmin(admin.ModelAdmin):
    list_display = ('submission_user', 'document_type', 'secure_preview', 'uploaded_at')
    list_filter = ('document_type',)
    search_fields = ('submission__user_full_name', 'submission__user_id')
    readonly_fields = ('id', 'secure_preview_large', 'uploaded_at')

    def submission_user(self, obj):
        return obj.submission.user_full_name if obj.submission_id else '—'

    submission_user.short_description = 'User'
    submission_user.admin_order_field = 'submission__user_full_name'

    def secure_preview(self, obj):
        """List view: small preview using .url (signed when bucket is private)."""
        if not obj or not obj.file:
            return mark_safe('<span class="quiet">—</span>')
        try:
            url = obj.file.url
        except Exception:
            return mark_safe('<span class="quiet">—</span>')
        return format_html(
            '<a href="{}" target="_blank" rel="noopener"><img src="{}" alt="{}" style="max-height:40px;max-width:60px;object-fit:contain;" /></a>',
            url, url, obj.document_type
        )

    secure_preview.short_description = 'Preview'

    def secure_preview_large(self, obj):
        """Change view: larger preview using .url (signed when bucket is private)."""
        if not obj or not obj.file:
            return mark_safe('<span class="quiet">—</span>')
        try:
            url = obj.file.url
        except Exception:
            return mark_safe('<span class="quiet">(unavailable)</span>')
        return format_html(
            '<a href="{}" target="_blank" rel="noopener"><img src="{}" alt="{}" style="max-height:300px;max-width:400px;object-fit:contain;" /></a>',
            url, url, obj.document_type
        )

    secure_preview_large.short_description = 'Document preview'


@admin.register(VerificationLog)
class VerificationLogAdmin(admin.ModelAdmin):
    list_display = ('submission', 'action', 'performed_by', 'created_at')
    list_filter = ('action',)
    search_fields = ('submission__user_full_name', 'performed_by')
    readonly_fields = ('id', 'created_at')
