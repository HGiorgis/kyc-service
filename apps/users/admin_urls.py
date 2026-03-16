from django.urls import path
from django.contrib.admin.views.decorators import staff_member_required
from . import admin_views

app_name = 'users'

urlpatterns = [
    path('dashboard/', staff_member_required(admin_views.admin_dashboard), name='dashboard'),
    path('kyc/', staff_member_required(admin_views.kyc_list), name='kyc-list'),
    path('kyc/<uuid:submission_id>/', staff_member_required(admin_views.kyc_review), name='kyc-review'),
    path('users/', staff_member_required(admin_views.user_list), name='users'),
    path('users/<uuid:user_id>/', staff_member_required(admin_views.user_detail), name='user-detail'),
    path('users/<uuid:user_id>/revoke-key/', staff_member_required(admin_views.revoke_user_key), name='revoke-key'),
    path('settings/', staff_member_required(admin_views.admin_settings), name='settings'),
    path('terminal/', staff_member_required(admin_views.terminal_view), name='terminal'),
    path('terminal/run/', staff_member_required(admin_views.terminal_run_command), name='terminal-run'),
]