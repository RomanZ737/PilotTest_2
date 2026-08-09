from django.urls import path
from django.urls import reverse_lazy
from .apps import UsersConfig
from .views import (
    # Аутентификация
    RegisterView,
    CustomLoginView,
    CustomLogoutView,
    UserUpdateView,
    VerifyEmailView,
    VerificationSentView,
    # Пилоты и группы
    UsersListView,
    UserDetailView,
    UserProfileView,
    PasswordChangeView,
    DeactivateUser,
    GroupListView,
    UserThemeUpdateView,
    GroupUpdateView,
    GroupDeleteView,
    GroupCreateView,
    GroupDetailView,
    GroupRemoveUserView,
)
from django.contrib.auth.views import (
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)


app_name = UsersConfig.name

urlpatterns = [
    # ============================================
    # Аутентификация
    # ============================================
    path('login/', CustomLoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', CustomLogoutView.as_view(next_page='/'), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('verify/<str:token>/', VerifyEmailView.as_view(), name='verify_email'),
    path('verification-sent/', VerificationSentView.as_view(), name='verification_sent'),

    path('password-reset/', PasswordResetView.as_view(
        template_name='users/password_reset_form.html',
        email_template_name='users/password_reset_email.html',
        subject_template_name='users/password_reset_subject.txt',
        success_url=reverse_lazy('users:password_reset_done')
    ), name='password_reset'),
    path('password-reset/done/', PasswordResetDoneView.as_view(
        template_name='users/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', PasswordResetConfirmView.as_view(
        template_name='users/password_reset_confirm.html',
        success_url=reverse_lazy('users:password_reset_complete')
    ), name='password_reset_confirm'),
    path('reset/done/', PasswordResetCompleteView.as_view(
        template_name='users/password_reset_complete.html'
    ), name='password_reset_complete'),

    # ============================================
    # Пилоты и группы
    # ============================================
    path('', UsersListView.as_view(), name='list'),
    path('<int:pk>/', UserDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', UserUpdateView.as_view(), name='edit'),
    path('<int:pk>/password/', PasswordChangeView.as_view(), name='password_change'),
    path('<int:pk>/deactivate/', DeactivateUser.as_view(), name='deactivate'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('groups/', GroupListView.as_view(), name='group_list'),
    path('<int:pk>/themes/', UserThemeUpdateView.as_view(), name='theme_update'),
    path('groups/<int:pk>/edit/', GroupUpdateView.as_view(), name='group_edit'),
    path('groups/<int:pk>/delete/', GroupDeleteView.as_view(), name='group_delete'),
    path('groups/create/', GroupCreateView.as_view(), name='group_create'),
    path('groups/<int:pk>/', GroupDetailView.as_view(), name='group_detail'),
    path('groups/<int:group_pk>/remove/<int:user_pk>/', GroupRemoveUserView.as_view(), name='group_remove_user'),
]