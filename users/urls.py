from django.urls import path
from django.urls import reverse_lazy
from .views import (
    RegisterView,
    CustomLoginView,
    CustomLogoutView,
    UserUpdateView,
    VerifyEmailView,
    VerificationSentView,
    UsersListView,
    DeactivateUser
    )
from django.contrib.auth.views import (
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)




app_name = 'users'

urlpatterns = [
    path('users/<int:pk>/deactivate', DeactivateUser.as_view(), name='deactivate'),
    path('users/list/', UsersListView.as_view(), name='list'),
    path('users/login/', CustomLoginView.as_view(template_name='users/login.html'), name='login'),
    path('users/logout/', CustomLogoutView.as_view(next_page='/'), name='logout'),
    path('users/register/', RegisterView.as_view(), name='register'),
    path('users/update/', UserUpdateView.as_view(), name='user_update'),
    path('users/verify/<str:token>/', VerifyEmailView.as_view(), name='verify_email'),
    path('users/verification-sent/', VerificationSentView.as_view(), name='verification_sent'),
    path('password-reset/', PasswordResetView.as_view(
                                                 template_name='users/password_reset_form.html',
                                                 email_template_name='users/password_reset_email.html',
                                                 subject_template_name='users/password_reset_subject.txt',
                                                 success_url=reverse_lazy('users:password_reset_done')
                                                ),
                                                name='password_reset'),
    path('password-reset/done/', PasswordResetDoneView.as_view(
                                                 template_name='users/password_reset_done.html'
                                                ),
                                                name='password_reset_done'),
    path('reset/<uidb64>/<token>/', PasswordResetConfirmView.as_view(
                                                 template_name='users/password_reset_confirm.html',
                                                 success_url=reverse_lazy('users:password_reset_complete')
                                                ),
                                                name='password_reset_confirm'),
    path('reset/done/', PasswordResetCompleteView.as_view(
                                                 template_name='users/password_reset_complete.html'
                                                ),
                                                name='password_reset_complete'),
]