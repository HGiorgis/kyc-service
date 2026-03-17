from django.urls import path
from .views.kyc_views import KYCSubmitView, KYCStatusView, KYCStatusBySubmissionIdView

urlpatterns = [
    path('kyc/submit/', KYCSubmitView.as_view(), name='kyc-submit'),
    path('kyc/status/<str:user_id>/', KYCStatusView.as_view(), name='kyc-status'),
    path('kyc/submission/<uuid:submission_id>/', KYCStatusBySubmissionIdView.as_view(), name='kyc-status-by-id'),
]