from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, UpdateView, View
from django.views.generic.detail import DetailView
from django.views.generic import ListView
from history.models import ActivityLog, TabView
from questions.services import reset_user_views
from .forms import CustomUserCreationForm, CustomUserForm
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from .models import CustomUser, GroupsDescription, UserTheme
from .services import generate_verification_token, send_verification_email, send_welcome_email
from django.contrib.auth import login
from django.views.generic import TemplateView
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, reverse, render
from django.http import HttpResponseForbidden
from django.contrib.auth.models import Group
from core.enums import ACType, Position
from django.db.models import Q
from django.contrib.auth.hashers import make_password
from questions.models import Themes
from history.services import log_activity
from django.utils.crypto import get_random_string
from django.utils import timezone


class DeactivateUser(PermissionRequiredMixin, LoginRequiredMixin, View):
    permission_required = "users.can_deactivate_user"

    def post(self, request, pk):
        user = get_object_or_404(CustomUser, id=pk)
        if not request.user.has_perm('users.can_deactivate_user'):
            return HttpResponseForbidden("У вас нет прав для блокировки пользователя.")
        if not user.is_active:
            user.is_active = True
        else:
            user.is_active = False

        action = 'blocked' if not user.is_active else 'unblocked'
        log_activity(
            user=request.user,
            entity_type='user',
            entity_id=user.pk,
            entity_name=user.get_full_name() or user.email,
            action_type=action,
        )

        user.save()
        return redirect('users:list')


class UsersListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = CustomUser
    template_name = 'users/user_list.html'
    context_object_name = 'users'
    permission_required = 'users.view_customuser'
    paginate_by = 25

    def get_queryset(self):

        queryset = super().get_queryset().prefetch_related('groups')
        # Скрываем суперпользователей из списка всех пилотов
        queryset = queryset.filter(is_superuser=False)

        # Поиск по ФИО / email
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(middle_name__icontains=search)
            )

        # Фильтр по группе
        group_id = self.request.GET.get('group')
        if group_id:
            queryset = queryset.filter(groups__id=group_id)

        # Фильтр по типу ВС
        ac_type = self.request.GET.get('ac_type')
        if ac_type:
            queryset = queryset.filter(ac_type=ac_type)

        # Фильтр по должности
        position = self.request.GET.get('position')
        if position:
            queryset = queryset.filter(position=position)

        # Фильтр по статусу
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'blocked':
            queryset = queryset.filter(is_active=False)

        return queryset.order_by('last_name', 'first_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Сохраняем текущие GET-параметры для пагинации
        params = self.request.GET.copy()
        if 'page' in params:
            params.pop('page')
        context['query_string'] = params.urlencode()

        # Данные для фильтров
        context['groups'] = Group.objects.all().order_by('name')
        context['ac_type_choices'] = ACType.choices
        context['position_choices'] = Position.choices

        # Текущие значения фильтров
        context['current_search'] = self.request.GET.get('search', '')
        context['current_group'] = self.request.GET.get('group', '')
        context['current_ac_type'] = self.request.GET.get('ac_type', '')
        context['current_position'] = self.request.GET.get('position', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['can_delete_users'] = (
                self.request.user.is_superuser or
                self.request.user.groups.filter(name='Администраторы').exists()
        )

        context['recent_activities'] = ActivityLog.objects.filter(
            entity_type__in=['user', 'group']
        ).select_related('user').order_by('-created_at')[:50]

        # Определяем, показывать ли историю
        context['show_history'] = (self.request.resolver_match.view_name == 'users:history')

        if context['show_history']:
            context['recent_activities'] = ActivityLog.objects.filter(
                entity_type__in=['user', 'group']
            ).select_related('user').order_by('-created_at')[:50]

            # Сбрасываем бейдж «new» при открытии истории
            if self.request.user.is_authenticated:
                TabView.objects.update_or_create(
                    user=self.request.user,
                    logical_question=None,
                    tab_type='user_list',
                    defaults={'viewed_at': timezone.now()}
                )
            context['history_has_new'] = False

        else:
            # Проверяем, есть ли новые события с момента последнего просмотра истории
            last_view = TabView.objects.filter(
                user=self.request.user,
                logical_question=None,
                tab_type='user_list'
            ).first()
            last_viewed = last_view.viewed_at if last_view else None

            new_activities = ActivityLog.objects.filter(
                entity_type__in=['user', 'group']
            ).exclude(user=self.request.user)

            if last_viewed:
                new_activities = new_activities.filter(created_at__gt=last_viewed)

            context['history_has_new'] = new_activities.exists()

        return context


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

        log_activity(
            user=user,
            entity_type='user',
            entity_id=user.pk,
            entity_name=user.get_full_name() or user.email,
            action_type='registered',
        )

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


class UserUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'users.change_customuser'
    model = CustomUser
    form_class = CustomUserForm
    template_name = 'users/user_form.html'


    # переопределяем has_permission для своего профиля
    def has_permission(self):
        pk = self.kwargs.get('pk')
        if pk and int(pk) == self.request.user.pk:
            return True
        return super().has_permission()

    def get_object(self, queryset=None):
        # Если передан pk — редактируем конкретного пилота, иначе — свой профиль
        pk = self.kwargs.get('pk')
        if pk:
            return get_object_or_404(CustomUser, pk=pk)
        return self.request.user

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        if pk:
            target_user = get_object_or_404(CustomUser, pk=pk)
            # Чужой профиль — нужны права
            if target_user != request.user and not request.user.has_perm('users.change_customuser'):
                messages.error(request, 'Вы можете редактировать только свой профиль.')
                return redirect('users:profile')
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        url = reverse('users:detail', kwargs={'pk': self.object.pk})
        back = self.request.GET.get('back', '')
        if back:
            url += f'?back={back}'
        return url

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['back_url'] = self.request.GET.get('back', '')
        return context

    def form_valid(self, form):
        old_groups = set(form.instance.groups.values_list('id', flat=True))
        response = super().form_valid(form)
        new_groups = set(form.instance.groups.values_list('id', flat=True))

        target_groups = Group.objects.filter(
            name__in=['Редактор', 'Супер Редактор', 'Администраторы']
        ).values_list('id', flat=True)
        target_ids = set(target_groups)

        if new_groups & target_ids and not old_groups & target_ids:
            # Пользователь впервые попал в одну из целевых групп
            reset_user_views(form.instance)

        return response


class GroupListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Group
    template_name = 'users/group_list.html'
    context_object_name = 'groups'
    permission_required = 'auth.view_group'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related('user_set')




        # Поиск по названию или описанию
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__description__icontains=search)
            )

        # Скрываем группу "Администраторы" от всех кроме суперпользователей
        if not self.request.user.is_superuser:
            queryset = queryset.exclude(name='Администраторы')
        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        params = self.request.GET.copy()
        if 'page' in params:
            params.pop('page')
        context['query_string'] = params.urlencode()
        context['current_search'] = self.request.GET.get('search', '')

        # Список фиксированных групп
        context['fixed_groups'] = GroupsDescription.objects.filter(
            is_fixed=True
        ).values_list('group__name', flat=True)

        # Словарь описаний групп (один запрос)
        descriptions = {
            d.group_id: d.description
            for d in GroupsDescription.objects.all()
        }

        for group in context['groups']:
            group.pilot_count = len(group.user_set.all())
            group.desc = descriptions.get(group.id, '—')

        return context


class UserDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = CustomUser
    template_name = 'users/user_detail.html'
    context_object_name = 'pilot'
    permission_required = 'users.view_customuser'

    def has_permission(self):
        if int(self.kwargs.get('pk', 0)) == self.request.user.pk:
            return True
        return super().has_permission()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['back_url'] = self.request.GET.get('back', reverse('users:list'))

        pilot = self.object

        # Темы — только если текущий пользователь может назначать темы
        if self.request.user.has_perm('users.can_change_user_themes'):
            editor_groups = pilot.groups.filter(name__in=['Редактор', 'Супер Редактор'])
            if editor_groups.exists():
                context['is_editor'] = True
                context['assigned_themes'] = UserTheme.objects.filter(
                    user=pilot
                ).select_related('theme')
                context['all_themes'] = Themes.objects.all().order_by('name')
                context['assigned_theme_ids'] = list(
                    UserTheme.objects.filter(user=pilot).values_list('theme_id', flat=True)
                )

        return context


class UserProfileView(LoginRequiredMixin, View):
    def get(self, request):
        return redirect('users:detail', pk=request.user.pk)


class PasswordChangeView(LoginRequiredMixin, View):
    """Смена пароля пилота."""

    def post(self, request, pk):
        pilot = get_object_or_404(CustomUser, pk=pk)

        # Проверка прав: свой профиль или есть право change_customuser
        if not (request.user == pilot or request.user.has_perm('users.change_customuser')):
            messages.error(request, 'У вас нет прав для смены пароля.')
            return redirect('users:detail', pk=pk)

        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        # Валидация
        if not new_password or not confirm_password:
            messages.error(request, 'Все поля обязательны.')
            return redirect('users:detail', pk=pk)

        if new_password != confirm_password:
            messages.error(request, 'Пароли не совпадают.')
            return redirect('users:detail', pk=pk)

        if len(new_password) < 5:
            messages.error(request, 'Пароль должен содержать минимум 5 символов.')
            return redirect('users:detail', pk=pk)

        # Меняем пароль
        pilot.password = make_password(new_password)
        pilot.save()

        messages.success(request, f'Пароль для {pilot.last_name} {pilot.first_name} успешно изменён.')
        return redirect('users:detail', pk=pk)


class UserThemeUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Обновление списка тем, назначенных пользователю."""
    permission_required = 'users.can_change_user_themes'

    def post(self, request, pk):
        pilot = get_object_or_404(CustomUser, pk=pk)

        # Только суперпользователь и Администраторы могут назначать темы
        if not (request.user.is_superuser or request.user.groups.filter(name='Администраторы').exists()):
            messages.error(request, 'Только суперпользователь может назначать темы.')
            return redirect('users:detail', pk=pk)

        # Получаем список ID тем из POST
        theme_ids = request.POST.getlist('theme_ids', [])
        theme_ids = [int(t) for t in theme_ids if t.isdigit()]

        # Удаляем старые связи
        UserTheme.objects.filter(user=pilot).delete()

        # Создаём новые
        for theme_id in theme_ids:
            theme = get_object_or_404(Themes, pk=theme_id)
            UserTheme.objects.get_or_create(user=pilot, theme=theme)

        messages.success(
            request,
            f'Темы для {pilot.last_name} {pilot.first_name} обновлены ({len(theme_ids)} шт.).'
        )
        return redirect('users:detail', pk=pk)


class GroupUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Редактирование группы (только суперпользователь)."""
    permission_required = 'auth.change_group'

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.groups.filter(name='Администраторы').exists()):
            messages.error(request, 'Только суперпользователь может редактировать группы.')
            return redirect('users:group_list')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        desc = GroupsDescription.objects.filter(group=group).first()

        context = {
            'group': group,
            'description': desc.description if desc else '',
            'is_fixed': desc.is_fixed if desc else False,
            'back_url': request.GET.get('back', reverse('users:group_list')),
        }
        return render(request, 'users/group_form.html', context)

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_fixed = request.POST.get('is_fixed') == 'on'

        if not name:
            messages.error(request, 'Название группы обязательно.')
            return redirect('users:group_edit', pk=pk)

        # Обновляем название
        group.name = name
        group.save()

        log_activity(
            user=request.user,
            entity_type='group',
            entity_id=group.pk,
            entity_name=group.name,
            action_type='updated',
        )

        # Обновляем описание
        desc, _ = GroupsDescription.objects.get_or_create(group=group)
        desc.description = description

        # is_fixed может менять только суперпользователь
        if request.user.is_superuser:
            desc.is_fixed = is_fixed
        desc.save()

        messages.success(request, f'Группа «{group.name}» обновлена.')
        back = request.POST.get('back', '') or request.GET.get('back', '')
        if back:
            return redirect(back)
        return redirect('users:group_list')


class GroupCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Создание новой группы (только суперпользователь)."""
    permission_required = 'auth.add_group'

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.groups.filter(name='Администраторы').exists()):
            messages.error(request, 'Только суперпользователь может создавать группы.')
            return redirect('users:group_list')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, 'users/group_form.html', {
            'group': None,
            'description': '',
            'is_fixed': False,
            'is_create': True,
            'back_url': request.GET.get('back', reverse('users:group_list')),
        })

    def post(self, request):
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_fixed = request.POST.get('is_fixed') == 'on'

        if not name:
            messages.error(request, 'Название группы обязательно.')
            return render(request, 'users/group_form.html', {
                'group': None,
                'description': description,
                'is_fixed': is_fixed,
                'is_create': True,
            })

        if Group.objects.filter(name=name).exists():
            messages.error(request, 'Группа с таким названием уже существует.')
            return render(request, 'users/group_form.html', {
                'group': None,
                'description': description,
                'is_fixed': is_fixed,
                'is_create': True,
            })

        group = Group.objects.create(name=name)
        GroupsDescription.objects.create(
            group=group,
            description=description,
            is_fixed=is_fixed,
        )

        log_activity(
            user=request.user,
            entity_type='group',
            entity_id=group.pk,
            entity_name=group.name,
            action_type='created',
        )

        messages.success(request, f'Группа «{group.name}» создана.')
        back = request.POST.get('back', '') or request.GET.get('back', '')
        if back:
            return redirect(back)
        return redirect('users:group_list')


class GroupDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Group
    template_name = 'users/group_detail.html'
    context_object_name = 'group'
    permission_required = 'auth.view_group'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = self.object

        desc = GroupsDescription.objects.filter(group=group).first()
        context['description'] = desc.description if desc else ''
        context['is_fixed'] = desc.is_fixed if desc else False
        context['pilots'] = group.user_set.all().order_by('last_name', 'first_name')
        context['back_url'] = self.request.GET.get('back', reverse('users:group_list'))
        # Пилоты, не входящие в группу
        context['available_pilots'] = CustomUser.objects.filter(
            is_superuser=False
        ).exclude(
            groups=group
        ).order_by('last_name', 'first_name')


        return context


class GroupDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Удаление группы (только суперпользователь или для нефиксированных)."""
    permission_required = 'auth.delete_group'

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        desc = GroupsDescription.objects.filter(group=group).first()

        # Фиксированные группы может удалить только суперпользователь
        if desc and desc.is_fixed and not request.user.is_superuser:
            messages.error(request, 'Эту группу может удалить только суперпользователь.')
            return redirect('users:group_list')

        log_activity(
            user=request.user,
            entity_type='group',
            entity_id=group.pk,
            entity_name=group.name,
            action_type='deleted',
        )

        group.delete()
        messages.success(request, f'Группа «{group.name}» удалена.')
        return redirect('users:group_list')


class GroupRemoveUserView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Удаление пилота из группы."""
    permission_required = 'auth.change_group'

    def post(self, request, group_pk, user_pk):
        group = get_object_or_404(Group, pk=group_pk)

        # if not request.user.is_superuser:
        #     messages.error(request, 'Только суперпользователь может удалять пилотов из группы.')
        #     return redirect('users:group_detail', pk=group_pk)

        pilot = get_object_or_404(CustomUser, pk=user_pk)
        group.user_set.remove(pilot)

        log_activity(
            user=request.user,
            entity_type='group',
            entity_id=group_pk,
            entity_name=group.name,
            action_type='updated',
            description=f'Удалён пилот: {pilot.get_full_name() or pilot.email}',
        )

        messages.success(
            request,
            f'{pilot.last_name} {pilot.first_name} удалён из группы «{group.name}».'
        )
        return redirect('users:group_detail', pk=group_pk)


class GroupAddUsersView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Добавление пилотов в группу."""
    permission_required = 'auth.change_group'

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)

        # if not request.user.is_superuser:
        #     messages.error(request, 'Только суперпользователь может добавлять пилотов в группу.')
        #     return redirect('users:group_detail', pk=pk)

        user_ids = request.POST.getlist('user_ids', [])
        added = 0
        for user_id in user_ids:
            pilot = get_object_or_404(CustomUser, pk=user_id)
            if not group.user_set.filter(pk=pilot.pk).exists():
                group.user_set.add(pilot)
                added += 1

        log_activity(
            user=request.user,
            entity_type='group',
            entity_id=group.pk,
            entity_name=group.name,
            action_type='updated',
            description=f'Добавлено пилотов: {added}',
        )

        messages.success(request, f'Добавлено пилотов в группу: {added}.')
        # Проверяем группу и добавляем записи о просмотренных вопросах
        # (что бы все вопросы небыли со статусом новые)

        if group.name in ['Редактор', 'Супер Редактор', 'Администраторы']:
            for user_id in user_ids:
                pilot = CustomUser.objects.get(pk=user_id)  # или уже есть объект
                reset_user_views(pilot)

        return redirect('users:group_detail', pk=pk)


class AdminUserCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Создание пилота администратором (KRS или суперпользователь)."""
    model = CustomUser
    template_name = 'users/user_form.html'
    form_class = CustomUserForm

    permission_required = 'users.add_customuser'

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.groups.filter(name='KRS').exists()):
            messages.error(request, 'У вас нет прав для создания пилотов.')
            return redirect('core:home')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save(commit=False)
        password = get_random_string(length=12)
        user.set_password(password)
        user.is_active = True
        user.is_email_verified = True
        user.save()
        form.save_m2m()

        if user.groups.filter(name__in=['Редактор', 'Супер Редактор', 'Администраторы']).exists():
            reset_user_views(user)

        log_activity(
            user=self.request.user,
            entity_type='user',
            entity_id=user.pk,
            entity_name=user.get_full_name() or user.email,
            action_type='created',
        )

        # Отправляем приветственное письмо
        try:
            send_welcome_email(user, password)
            messages.success(
                self.request,
                f'Пилот {user.get_full_name()} создан. Пароль отправлен на {user.email}.'
            )
        except Exception:
            messages.success(
                self.request,
                f'Пилот {user.get_full_name()} создан. Временный пароль: {password}'
            )



        return redirect('users:detail', pk=user.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_create'] = True
        context['back_url'] = reverse('users:list')
        return context


class UserDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Удаление пилота (только суперпользователь или Администраторы)."""

    permission_required = 'users.delete_customuser'

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.groups.filter(name='Администраторы').exists()):
            messages.error(request, 'У вас нет прав для удаления пилотов.')
            return redirect('core:home')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        pilot = get_object_or_404(CustomUser, pk=pk)

        if pilot.is_superuser:
            messages.error(request, 'Нельзя удалить суперпользователя.')
            return redirect('users:list')

        email = pilot.email

        log_activity(
            user=request.user,
            entity_type='user',
            entity_id=pilot.pk,
            entity_name=pilot.get_full_name() or pilot.email,
            action_type='deleted',
        )


        pilot.delete()
        messages.success(request, f'Пилот {email} удалён.')
        return redirect('users:list')