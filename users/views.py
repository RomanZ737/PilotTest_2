from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, UpdateView, View
from django.views.generic import ListView
from .forms import CustomUserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from .models import CustomUser
from .services import generate_verification_token, send_verification_email
from django.contrib.auth import login
from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponseForbidden


class DeactivateUser(LoginRequiredMixin, View):
    def post(self, request, pk):
        user = get_object_or_404(CustomUser, id=pk)
        if not request.user.has_perm('users.can_deactivate_user'):
            return HttpResponseForbidden("У вас нет прав для блокировки пользователя.")
        if not user.is_active:
            user.is_active = True
        else:
            user.is_active = False
        user.save()
        return redirect('users:list')

class UsersListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = CustomUser
    template_name = 'users/user_list.html'
    context_object_name = 'users'
    permission_required = 'users.view_customuser'


class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    success_url = reverse_lazy('core:home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context



class CustomLogoutView(LogoutView):
    def get_next_page(self):
        return reverse_lazy('login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class RegisterView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('users:verification_sent')


    def form_valid(self, form):
        user = form.save(commit=False)
        user.is_active = False
        user.is_email_verified = False
        user.email_verification_token = generate_verification_token()
        user.save()
        try:
            send_verification_email(user, self.request)
        except Exception as e:
            print(e)
        self.request.session['pending_verification_email'] = user.email
        return redirect('users:verification_sent')


class VerifyEmailView(View):
    def get(self, request, token):
        try:
            user = CustomUser.objects.get(email_verification_token=token)
        except CustomUser.DoesNotExist:
            messages.error(request, 'Ссылка недействительна или уже использована.')
            return redirect('users:login')

        user.is_active = True
        user.is_email_verified = True
        user.email_verification_token = ''  # очищаем токен
        user.save()

        messages.success(request, 'Email успешно подтверждён! Теперь вы можете войти.')

        login(request, user)
        return redirect('core:home')


class VerificationSentView(TemplateView):
    template_name = 'users/verification_sent.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Получаем email из сессии и сразу удаляем (чтобы не хранить)
        context['user_email'] = self.request.session.pop('pending_verification_email', None)
        return context

class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    fields = ['username', 'first_name', 'last_name', 'email', 'phone_number']
    template_name = 'users/register.html'
    success_url = reverse_lazy('core:home')


    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context