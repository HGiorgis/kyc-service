from django.urls import path
from .views import kyc_views  # This is wrong - should be from .views.kyc_views

# CORRECTED VERSION:
from .views.kyc_views import KYCSubmitView, KYCStatusView

urlpatterns = [
    path('kyc/submit/', KYCSubmitView.as_view(), name='kyc-submit'),
    path('kyc/status/<str:user_id>/', KYCStatusView.as_view(), name='kyc-status'),
]