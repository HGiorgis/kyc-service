# This file makes the views directory a Python package
from .kyc_views import KYCSubmitView, KYCStatusView

__all__ = ['KYCSubmitView', 'KYCStatusView']