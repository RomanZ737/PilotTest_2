from django.urls import reverse_lazy
from django.views.generic import ListView, View, CreateView, UpdateView, DeleteView, DetailView
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Prefetch

from history.models import QuestionHistory, Comment, Action, DraftView, TabView
from history.services import log_activity
from .forms import QuestionForm, AnswerFormSetFactory, ThemeForm, DraftForm, DraftAnswerFormSetFactory, ParaphraseForm
from .models import Question, Themes, Answer, QuestionDraft, QuestionParaphrase
from core.enums import ACType
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse
from history.models import ActivityLog
from questions.services import get_user_themes, get_new_questions_queryset, has_new_themes, reset_question_views, \
    reset_theme_views
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q, Count


class QuestionListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Question
    template_name = 'questions/list.html'
    context_object_name = 'question_list'
    permission_required = 'questions.view_question'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().select_related('theme')
        queryset = queryset.prefetch_related('paraphrases', 'drafts')
        #queryset = queryset.filter(is_archived=False)

        available_themes = get_user_themes(self.request.user)
        queryset = queryset.filter(theme__in=available_themes)

        if self.request.GET.get('new_only') == '1':
            queryset = get_new_questions_queryset(self.request.user, queryset)

        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(question__icontains=search)

        theme_id = self.request.GET.get('theme')
        if theme_id:
            queryset = queryset.filter(theme_id=theme_id)

        ac_type = self.request.GET.get('ac_type')
        if ac_type:
            queryset = queryset.filter(ac_type=ac_type)

        status = self.request.GET.get('status')
        if status == 'published':
            queryset = queryset.filter(is_published=True, is_archived=False)
        elif status == 'unpublished':
            queryset = queryset.filter(is_published=False, is_archived=False)
        elif status == 'draft':
            queryset = queryset.filter(drafts__isnull=False, is_archived=False)
        elif status == 'paraphrase':
            queryset = queryset.filter(paraphrases__isnull=False, is_archived=False)
        elif status == 'archived':
            queryset = queryset.filter(previous_version__isnull=False, is_archived=False)
        else:
            queryset = queryset.filter(is_archived=False)

        return queryset.order_by('theme__name', 'question')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        params = self.request.GET.copy()
        params.pop('page', None)
        #params.pop('new_only', None)
        context['query_string'] = params.urlencode()

        context['themes'] = get_user_themes(self.request.user).order_by('name')
        context['ac_type_choices'] = ACType.choices
        context['current_filters'] = self.request.GET.copy()

        # Пометка вопросов для колонки "Изменения"
        if self.request.user.is_authenticated:
            for question in context['question_list']:
                last_view = TabView.objects.filter(
                    user=self.request.user,
                    logical_question=question,
                    tab_type='question'
                ).first()
                if not last_view or last_view.viewed_at < question.updated_at:
                    question.is_new = True
                else:
                    question.is_new = False

        # Флаг для бейджа на вкладке "Вопросы"

        # context['new_questions_exist'] = has_new_questions(self.request.user)
        # context['new_questions_count'] = 0

        # from questions.services import has_new_themes
        # context['new_themes_exist'] = has_new_themes(self.request.user)

        last_view = TabView.objects.filter(
            user=self.request.user,
            logical_question=None,
            tab_type='question_history'
        ).first()
        last_viewed = last_view.viewed_at if last_view else None

        new_activities = ActivityLog.objects.filter(
            entity_type__in=['question', 'theme']
        ).exclude(user=self.request.user)

        available_themes = get_user_themes(self.request.user)
        if not self.request.user.is_superuser:
            new_activities = new_activities.filter(theme__in=available_themes)

        if last_viewed:
            new_activities = new_activities.filter(created_at__gt=last_viewed)

        # context['history_has_new'] = new_activities.exists()

        context['recent_activities'] = ActivityLog.objects.filter(
            entity_type__in=['question', 'theme']
        ).select_related('user', 'theme').order_by('-created_at')[:50]

        context['show_history'] = (self.request.resolver_match.view_name == 'questions:history')

        if context['show_history']:
            if self.request.user.is_authenticated:
                TabView.objects.update_or_create(
                    user=self.request.user,
                    logical_question=None,
                    tab_type='question_history',
                    defaults={'viewed_at': timezone.now()}
                )
                context['history_has_new'] = False

        context['show_new_only'] = (self.request.GET.get('new_only') == '1')
        return context


class QuestionDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Question
    template_name = 'questions/question_detail.html'
    context_object_name = 'question'
    permission_required = 'questions.view_question'

    def get_object(self, queryset=None):
        return get_object_or_404(
            Question.objects.select_related('theme', 'created_by')
            .prefetch_related(
                'answers',
                'drafts',
                'paraphrases',
                Prefetch(
                    'history',
                    queryset=QuestionHistory.objects.select_related('user')
                    .prefetch_related(
                        Prefetch('actions'),
                        Prefetch('comments', queryset=Comment.objects.select_related('user'))
                    )
                )
            ),
            pk=self.kwargs['pk']
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        question = self.get_object()

        draft = question.drafts.order_by('-updated_at').first()
        if draft:
            context['draft'] = draft
            if self.request.user.is_authenticated:
                tab_view, created = TabView.objects.update_or_create(
                    user=self.request.user,
                    logical_question=question,
                    tab_type='draft',
                    defaults={'viewed_at': timezone.now()}
                )
                context['draft'].is_new = created

        paraphrase = question.paraphrases.first()
        if paraphrase:
            context['paraphrase'] = paraphrase
            if self.request.user.is_authenticated:
                tab_view, created = TabView.objects.update_or_create(
                    user=self.request.user,
                    logical_question=question,
                    tab_type='paraphrase',
                    defaults={'viewed_at': timezone.now()}
                )
                context['paraphrase'].is_new = created

        if self.request.user.is_authenticated:
            tab_view, created = TabView.objects.update_or_create(
                user=self.request.user,
                logical_question=question,
                tab_type='question',
                defaults={'viewed_at': timezone.now()}
            )
            context['question'].is_new = created

        history_qs = question.history.all()

        user_filter = self.request.GET.get('user')
        if user_filter:
            history_qs = history_qs.filter(
                Q(user__username__icontains=user_filter) |
                Q(user__first_name__icontains=user_filter) |
                Q(user__last_name__icontains=user_filter) |
                Q(user__email__icontains=user_filter)
            )

        action_filter = self.request.GET.get('action')
        if action_filter and action_filter != 'all':
            history_qs = history_qs.filter(actions__action_type=action_filter).distinct()

        sort = self.request.GET.get('sort', 'date_desc')
        if sort == 'date_asc':
            history_qs = history_qs.order_by('created_at')
        else:
            history_qs = history_qs.order_by('-created_at')

        context['history'] = history_qs
        context['last_comment'] = Comment.objects.filter(
            history__logical_question=question
        ).order_by('-created_at').first()
        context['back_url'] = self.request.GET.get('back', reverse('questions:question_list'))
        return context


class QuestionPublishView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'questions.can_publish'

    def post(self, request, pk):
        question = get_object_or_404(Question, pk=pk)

        if question.is_archived:
            messages.error(request, 'Нельзя изменить статус архивного вопроса.')
            return redirect('questions:question_list')

        comment_text = request.POST.get('comment', '').strip()

        if not comment_text:
            messages.error(request, 'Для изменения статуса вопроса необходимо оставить комментарий.')
            redirect_to = request.POST.get('redirect_to', '')
            if redirect_to == 'list':
                return redirect('questions:question_list')
            return redirect('questions:question_detail', pk=pk)

        if question.is_published:
            question.is_published = False
            action_type = 'unpublished'
            messages.warning(request, f'Вопрос снят с публикации и НЕ будет использован в тестах. '
                                      f'{"Перефраз снят с публикации" if question.paraphrases.exists() else ""}')
        else:
            question.is_published = True
            question.published_at = timezone.now()
            action_type = 'published'
            messages.success(request, f'Вопрос опубликован и будет использовать в тестах.')
        question.save()

        if action_type == 'unpublished':
            for paraphrase in question.paraphrases.filter(is_published=True):
                paraphrase.is_published = False
                paraphrase.save()
                ph_history = QuestionHistory.objects.create(
                    logical_question=question,
                    entity_type='paraphrase',
                    user=request.user,
                    user_name=request.user.get_full_name() or request.user.username,
                )
                Action.objects.create(history=ph_history, action_type='unpublished')

        history = QuestionHistory.objects.create(
            logical_question=question,
            entity_type='question',
            user=request.user,
            user_name=request.user.get_full_name() or request.user.username
        )
        Action.objects.create(history=history, action_type=action_type)
        Comment.objects.create(
            history=history,
            user=request.user,
            user_name=request.user.get_full_name() or request.user.username,
            text=comment_text,
        )

        TabView.objects.filter(
            logical_question=question,
            tab_type='question',
        ).exclude(user=request.user).delete()

        TabView.objects.update_or_create(
            user=request.user,
            logical_question=question,
            tab_type='question',
            defaults={'viewed_at': timezone.now()}
        )

        redirect_to = request.POST.get('redirect_to', '')
        if redirect_to == 'list':
            return redirect('questions:question_list')
        return redirect('questions:question_detail', pk=question.pk)


class QuestionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Question
    form_class = QuestionForm
    template_name = 'questions/question_form.html'
    permission_required = 'questions.add_question'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['theme_form'] = ThemeForm()
        if self.request.POST:
            context['answer_formset'] = AnswerFormSetFactory(
                self.request.POST,
                instance=self.object
            )
        else:
            formset = AnswerFormSetFactory(instance=self.object)
            context['answer_formset'] = formset
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        answer_formset = context['answer_formset']

        if not answer_formset.is_valid():
            return self.render_to_response(context)

        form.instance.created_by = self.request.user
        self.object = form.save()

        answer_formset.instance = self.object
        answers = answer_formset.save(commit=False)
        for i, answer in enumerate(answers, start=1):
            answer.answer_order = i
            answer.save()
        for obj in answer_formset.deleted_objects:
            obj.delete()

        request = self.request
        history = QuestionHistory.objects.create(
            logical_question=self.object,
            entity_type='question',
            user=self.request.user,
            user_name=request.user.get_full_name() or request.user.username
        )
        Action.objects.create(history=history, action_type='created')

        TabView.objects.filter(
            logical_question=self.object,
            tab_type='question',
        ).exclude(user=self.request.user).delete()

        TabView.objects.update_or_create(
            user=self.request.user,
            logical_question=self.object,
            tab_type='question',
            defaults={'viewed_at': timezone.now()}
        )

        messages.success(self.request, f'Вопрос #{self.object.pk} успешно создан.')
        return redirect('questions:question_detail', pk=self.object.pk)

    def form_invalid(self, form):
        context = self.get_context_data()
        return self.render_to_response(context)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class QuestionDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'questions.delete_question'

    def post(self, request, pk):
        question = get_object_or_404(Question, pk=pk)

        # Логируем удаление вопроса в общий журнал (сквозную историю)
        log_activity(
            user=request.user,
            entity_type='question',
            entity_id=question.pk,
            entity_name=question.question[:100],
            action_type='deleted',
            theme=question.theme,
        )

        question.delete()
        messages.success(request, f'Вопрос #{pk} удалён.')
        return redirect('questions:question_list')


class ThemesListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Themes
    template_name = 'questions/themes_list.html'
    context_object_name = 'themes_list'
    permission_required = 'questions.view_themes'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset()
        available_themes = get_user_themes(self.request.user)
        queryset = queryset.filter(id__in=available_themes)

        if self.request.GET.get('new_only') == '1':
            new_theme_ids = []
            for theme in queryset:
                last_view = TabView.objects.filter(
                    user=self.request.user,
                    theme=theme,
                    tab_type='theme'
                ).first()
                if not last_view or last_view.viewed_at < theme.updated_at:
                    new_theme_ids.append(theme.pk)
            queryset = queryset.filter(pk__in=new_theme_ids)

        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        queryset = queryset.annotate(
            question_count=Count('question', filter=Q(question__is_archived=False))
        )
        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        params = self.request.GET.copy()
        params.pop('page', None)
        #params.pop('new_only', None)
        context['query_string'] = params.urlencode()

        for theme in context['themes_list']:
            last_view = TabView.objects.filter(
                user=self.request.user,
                theme=theme,
                tab_type='theme'
            ).first()
            if not last_view or last_view.viewed_at < theme.updated_at:
                theme.is_new = True
            else:
                theme.is_new = False

        # from questions.services import has_new_questions, has_new_themes
        # context['new_questions_exist'] = has_new_questions(self.request.user)
        # context['new_themes_exist'] = has_new_themes(self.request.user)

        last_view = TabView.objects.filter(
            user=self.request.user,
            logical_question=None,
            tab_type='question_history'
        ).first()
        last_viewed = last_view.viewed_at if last_view else None

        new_activities = ActivityLog.objects.filter(
            entity_type__in=['question', 'theme']
        ).exclude(user=self.request.user)

        available_themes = get_user_themes(self.request.user)
        if not self.request.user.is_superuser:
            new_activities = new_activities.filter(theme__in=available_themes)

        if last_viewed:
            new_activities = new_activities.filter(created_at__gt=last_viewed)

        # context['history_has_new'] = new_activities.exists()
        context['show_new_only'] = (self.request.GET.get('new_only') == '1')
        return context


class ThemesDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Themes
    template_name = 'questions/theme_detail.html'
    context_object_name = 'theme'
    permission_required = 'questions.view_themes'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        theme = self.object

        if self.request.user.is_authenticated:
            TabView.objects.update_or_create(
                user=self.request.user,
                theme=self.object,
                logical_question=None,
                tab_type='theme',
                defaults={'viewed_at': timezone.now()}
            )

        context['question_count'] = theme.question_set.count()
        return context


class ThemesUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Themes
    form_class = ThemeForm
    template_name = 'questions/theme_form.html'
    permission_required = 'questions.change_themes'
    success_url = reverse_lazy('questions:themes_list')

    def form_valid(self, form):
        response = super().form_valid(form)

        TabView.objects.filter(
            theme=self.object,
            tab_type='theme',
        ).exclude(user=self.request.user).delete()

        TabView.objects.update_or_create(
            user=self.request.user,
            theme=self.object,
            logical_question=None,
            tab_type='theme',
            defaults={'viewed_at': timezone.now()}
        )
        return response


class ThemesDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'questions.delete_themes'

    def post(self, request, pk):
        theme = get_object_or_404(Themes, pk=pk)

        # Логируем удаление темы в общий журнал (сквозную историю)
        log_activity(
            user=request.user,
            entity_type='theme',
            entity_id=theme.pk,
            entity_name=theme.name,
            action_type='deleted',
        )

        theme.delete()
        messages.success(request, f'Тема #{pk} удалена.')
        return redirect('questions:themes_list')


class ThemesCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Themes
    form_class = ThemeForm
    template_name = 'questions/theme_form.html'
    permission_required = 'questions.add_themes'
    success_url = reverse_lazy('questions:themes_list')

    def form_valid(self, form):
        self.object = form.save()

        TabView.objects.filter(
            theme=self.object,
            tab_type='theme',
        ).exclude(user=self.request.user).delete()

        TabView.objects.update_or_create(
            user=self.request.user,
            theme=self.object,
            logical_question=None,
            tab_type='theme',
            defaults={'viewed_at': timezone.now()}
        )

        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'id': self.object.id,
                'name': self.object.name,
            })

        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string(
                'questions/includes/theme_modal_form.html',
                {'form': form},
                request=self.request
            )
            return JsonResponse({'success': False, 'html': html})

        return super().form_invalid(form)


class DraftCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'questions.add_questiondraft'

    def post(self, request, pk):
        question = get_object_or_404(Question, pk=pk)

        if question.drafts.exists():
            draft = question.drafts.first()
            messages.warning(request, 'Черновик уже существует.')
            return redirect('questions:question_detail', pk=pk)

        draft = QuestionDraft.objects.create(
            original_question=question,
            question=question.question,
            theme=question.theme,
            ac_type=question.ac_type,
            q_kind=question.q_kind,
            q_weight=question.q_weight,
            is_time_limited=question.is_time_limited,
            question_img=question.question_img,
            comment_img=question.comment_img,
            comment_text=question.comment_text,
            created_by=request.user,
        )

        for answer in question.answers.all():
            Answer.objects.create(
                question_draft=draft,
                answer=answer.answer,
                is_correct=answer.is_correct,
                answer_order=answer.answer_order,
            )

        history = QuestionHistory.objects.create(
            logical_question=question,
            entity_type='draft',
            user=request.user,
            user_name=request.user.get_full_name() or request.user.username,
        )
        Action.objects.create(history=history, action_type='created')

        # Сброс просмотров черновика
        TabView.objects.update_or_create(
            user=request.user,
            logical_question=question,
            tab_type='draft',
            defaults={'viewed_at': timezone.now()}
        )
        TabView.objects.filter(
            logical_question=question,
            tab_type='draft',
        ).exclude(user=request.user).delete()

        # Сброс просмотров основного вопроса (чтобы он стал новым для других)
        TabView.objects.filter(
            logical_question=question,
            tab_type='question',
        ).exclude(user=request.user).delete()
        TabView.objects.update_or_create(
            user=request.user,
            logical_question=question,
            tab_type='question',
            defaults={'viewed_at': timezone.now()}
        )

        messages.success(request, 'Черновик создан.')
        return redirect('questions:draft_edit', pk=draft.pk)


class DraftUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'questions.change_questiondraft'
    model = QuestionDraft
    form_class = DraftForm
    template_name = 'questions/draft_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        draft = self.get_object()
        context['draft'] = draft
        if self.request.POST:
            context['answer_formset'] = DraftAnswerFormSetFactory(
                self.request.POST,
                self.request.FILES,
                instance=draft
            )
        else:
            context['answer_formset'] = DraftAnswerFormSetFactory(instance=draft)
        context['theme_form'] = ThemeForm()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        answer_formset = context['answer_formset']

        if not answer_formset.is_valid():
            return self.render_to_response(context)

        has_changes = form.has_changed()
        if not has_changes:
            for answer_form in answer_formset:
                if answer_form.has_changed():
                    has_changes = True
                    break
            for answer_form in answer_formset.forms:
                if not answer_form.cleaned_data.get('id') and not answer_form.cleaned_data.get('DELETE', False):
                    has_changes = True
                    break
            if any(answer_form.cleaned_data.get('DELETE', False) for answer_form in answer_formset.forms if
                   answer_form.cleaned_data):
                has_changes = True

        comment_text = self.request.POST.get('comment', '').strip()
        if has_changes and not comment_text:
            messages.warning(self.request, 'При сохранении изменений комментарий обязателен.')
            return self.render_to_response(context)

        self.object = form.save()
        answer_formset.instance = self.object
        answers = answer_formset.save(commit=False)
        for i, answer in enumerate(answers, start=1):
            answer.answer_order = i
            answer.save()
        for obj in answer_formset.deleted_objects:
            obj.delete()

        if has_changes:
            history = QuestionHistory.objects.create(
                logical_question=self.object.original_question,
                entity_type='draft',
                user=self.request.user,
                user_name=self.request.user.get_full_name() or self.request.user.username,
            )
            Action.objects.create(history=history, action_type='updated_field')
            if comment_text:
                Comment.objects.create(
                    history=history,
                    user=self.request.user,
                    user_name=self.request.user.get_full_name() or self.request.user.username,
                    text=comment_text,
                )
            messages.success(self.request, 'Черновик сохранён.')
        else:
            messages.info(self.request, 'Нет изменений для сохранения.')

        # Сброс просмотров черновика
        TabView.objects.filter(
            logical_question=self.object.original_question,
            tab_type='draft',
        ).exclude(user=self.request.user).delete()
        TabView.objects.update_or_create(
            user=self.request.user,
            logical_question=self.object.original_question,
            tab_type='draft',
            defaults={'viewed_at': timezone.now()}
        )

        # Сброс просмотров основного вопроса (чтобы он стал новым для других)
        TabView.objects.filter(
            logical_question=self.object.original_question,
            tab_type='question',
        ).exclude(user=self.request.user).delete()
        TabView.objects.update_or_create(
            user=self.request.user,
            logical_question=self.object.original_question,
            tab_type='question',
            defaults={'viewed_at': timezone.now()}
        )

        url = reverse('questions:question_detail', kwargs={'pk': self.object.original_question.pk})
        return redirect(f'{url}?tab=draft')


class DraftPublishView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'questions.can_publish'

    def post(self, request, pk):
        draft = get_object_or_404(QuestionDraft, pk=pk)
        original = draft.original_question

        if original.previous_version:
            original.previous_version.delete()

        archived = Question.objects.create(
            question=original.question,
            theme=original.theme,
            ac_type=original.ac_type,
            q_kind=original.q_kind,
            q_weight=original.q_weight,
            is_time_limited=original.is_time_limited,
            question_img=original.question_img,
            comment_img=original.comment_img,
            comment_text=original.comment_text,
            is_published=False,
            is_archived=True,
            created_by=original.created_by,
        )

        for answer in original.answers.all():
            Answer.objects.create(
                question=archived,
                answer=answer.answer,
                is_correct=answer.is_correct,
                answer_order=answer.answer_order,
            )

        original.question = draft.question
        original.theme = draft.theme
        original.ac_type = draft.ac_type
        original.q_kind = draft.q_kind
        original.q_weight = draft.q_weight
        original.is_time_limited = draft.is_time_limited
        original.question_img = draft.question_img
        original.comment_img = draft.comment_img
        original.comment_text = draft.comment_text
        original.is_published = True
        original.published_at = timezone.now()
        original.previous_version = archived
        original.save()

        original.answers.all().delete()
        for draft_answer in draft.answers.all():
            Answer.objects.create(
                question=original,
                answer=draft_answer.answer,
                is_correct=draft_answer.is_correct,
                answer_order=draft_answer.answer_order,
            )

        draft.delete()

        for paraphrase in original.paraphrases.filter(is_published=True):
            paraphrase.is_published = False
            paraphrase.save()
            ph_history = QuestionHistory.objects.create(
                logical_question=original,
                entity_type='paraphrase',
                user=request.user,
                user_name=request.user.get_full_name() or request.user.username,
            )
            Action.objects.create(history=ph_history, action_type='unpublished')

        history = QuestionHistory.objects.create(
            logical_question=original,
            entity_type='draft',
            user=request.user,
            user_name=request.user.get_full_name() or request.user.username,
        )
        Action.objects.create(history=history, action_type='published')

        comment_text = request.POST.get('comment', '').strip()
        if comment_text:
            Comment.objects.create(
                history=history,
                user=request.user,
                user_name=request.user.get_full_name() or request.user.username,
                text=comment_text,
            )

        # Сброс просмотров основного вопроса
        TabView.objects.filter(
            logical_question=original,
            tab_type='question',
        ).exclude(user=request.user).delete()
        TabView.objects.update_or_create(
            user=request.user,
            logical_question=original,
            tab_type='question',
            defaults={'viewed_at': timezone.now()}
        )

        messages.success(request, f'Черновик опубликован.<br>'
                                  f'{"Перефраз снят с публикации" if original.paraphrases.exists() else ""}')
        return redirect('questions:question_detail', pk=original.pk)


class DraftDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'questions.delete_questiondraft'

    def post(self, request, pk):
        draft = get_object_or_404(QuestionDraft, pk=pk)
        question_pk = draft.original_question.pk

        history = QuestionHistory.objects.create(
            logical_question=draft.original_question,
            entity_type='draft',
            user=request.user,
            user_name=request.user.get_full_name() or request.user.username,
        )
        Action.objects.create(history=history, action_type='deleted')

        draft.delete()

        # Сброс просмотров основного вопроса (чтобы он стал новым для других)
        question = draft.original_question
        TabView.objects.filter(
            logical_question=question,
            tab_type='question',
        ).exclude(user=request.user).delete()
        TabView.objects.update_or_create(
            user=request.user,
            logical_question=question,
            tab_type='question',
            defaults={'viewed_at': timezone.now()}
        )

        messages.success(request, 'Черновик удалён.')
        return redirect('questions:question_detail', pk=question_pk)


class ArchiveRestoreView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'questions.can_restore'

    def post(self, request, pk):
        question = get_object_or_404(Question, pk=pk)
        archived = question.previous_version

        draft_question = question.question
        draft_theme = question.theme
        draft_ac_type = question.ac_type
        draft_q_kind = question.q_kind
        draft_q_weight = question.q_weight
        draft_is_time_limited = question.is_time_limited
        draft_question_img = question.question_img
        draft_comment_img = question.comment_img
        draft_comment_text = question.comment_text

        question.question = archived.question
        question.theme = archived.theme
        question.ac_type = archived.ac_type
        question.q_kind = archived.q_kind
        question.q_weight = archived.q_weight
        question.is_time_limited = archived.is_time_limited
        question.question_img = archived.question_img
        question.comment_img = archived.comment_img
        question.comment_text = archived.comment_text
        question.is_published = False
        question.published_at = None
        question.previous_version = None
        question.save()

        draft = QuestionDraft.objects.create(
            original_question=question,
            question=draft_question,
            theme=draft_theme,
            ac_type=draft_ac_type,
            q_kind=draft_q_kind,
            q_weight=draft_q_weight,
            is_time_limited=draft_is_time_limited,
            question_img=draft_question_img,
            comment_img=draft_comment_img,
            comment_text=draft_comment_text,
            created_by=request.user,
        )

        for answer in question.answers.all():
            Answer.objects.create(
                question_draft=draft,
                answer=answer.answer,
                is_correct=answer.is_correct,
                answer_order=answer.answer_order,
            )
        question.answers.all().delete()

        for archived_answer in archived.answers.all():
            Answer.objects.create(
                question=question,
                answer=archived_answer.answer,
                is_correct=archived_answer.is_correct,
                answer_order=archived_answer.answer_order,
            )

        archived.delete()

        para_message = False
        for paraphrase in question.paraphrases.filter(is_published=True):
            paraphrase.is_published = False
            para_message = True
            paraphrase.save()
            ph_history = QuestionHistory.objects.create(
                logical_question=question,
                entity_type='paraphrase',
                user=request.user,
                user_name=request.user.get_full_name() or request.user.username,
            )
            Action.objects.create(history=ph_history, action_type='unpublished')

        history = QuestionHistory.objects.create(
            logical_question=question,
            entity_type='question',
            user=request.user,
            user_name=request.user.get_full_name() or request.user.username,
        )
        Action.objects.create(history=history, action_type='restored')

        comment_text = request.POST.get('comment', '').strip()
        if comment_text:
            Comment.objects.create(
                history=history,
                user=request.user,
                user_name=request.user.get_full_name() or request.user.username,
                text=comment_text,
            )

        TabView.objects.filter(
            logical_question=question,
            tab_type='question',
        ).exclude(user=request.user).delete()
        TabView.objects.update_or_create(
            user=request.user,
            logical_question=question,
            tab_type='question',
            defaults={'viewed_at': timezone.now()}
        )

        messages.success(request, f'Архивная версия восстановлена.<br>Текущая версия сохранена как черновик.<br>'
                                  f'{"Перефраз снят с публикации" if para_message else ""}')
        return redirect('questions:question_detail', pk=question.pk)


class ParaphraseCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = QuestionParaphrase
    form_class = ParaphraseForm
    template_name = 'questions/paraphrase_form.html'
    permission_required = 'questions.add_questionparaphrase'

    def dispatch(self, request, *args, **kwargs):
        self.original_question = get_object_or_404(Question, pk=self.kwargs['pk'])
        if self.original_question.paraphrases.exists():
            messages.warning(request, 'Перефраз для этого вопроса уже существует.')
            return redirect(
                reverse('questions:question_detail', kwargs={'pk': self.original_question.pk})
                + '?tab=paraphrase'
            )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['initial'] = {
            'theme': self.original_question.theme,
            'ac_type': self.original_question.ac_type,
            'q_kind': self.original_question.q_kind,
            'q_weight': self.original_question.q_weight,
            'is_time_limited': self.original_question.is_time_limited,
        }
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['original_question'] = self.original_question
        context['answers'] = self.original_question.get_answers()
        context['is_create'] = True
        return context

    def form_valid(self, form):
        form.instance.original_question = self.original_question
        form.instance.created_by = self.request.user
        paraphrase = form.save()

        history = QuestionHistory.objects.create(
            logical_question=self.original_question,
            entity_type='paraphrase',
            user=self.request.user,
            user_name=self.request.user.get_full_name() or self.request.user.username,
        )
        Action.objects.create(history=history, action_type='created')

        messages.success(self.request, 'Перефраз успешно создан.')

        # Сброс просмотров перефраза
        TabView.objects.filter(
            logical_question=self.original_question,
            tab_type='paraphrase',
        ).exclude(user=self.request.user).delete()
        TabView.objects.update_or_create(
            user=self.request.user,
            logical_question=self.original_question,
            tab_type='paraphrase',
            defaults={'viewed_at': timezone.now()}
        )

        # Сброс просмотров основного вопроса
        TabView.objects.filter(
            logical_question=self.original_question,
            tab_type='question',
        ).exclude(user=self.request.user).delete()
        TabView.objects.update_or_create(
            user=self.request.user,
            logical_question=self.original_question,
            tab_type='question',
            defaults={'viewed_at': timezone.now()}
        )

        url = reverse('questions:question_detail', kwargs={'pk': self.original_question.pk})
        return redirect(f'{url}?tab=paraphrase')


class ParaphraseUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = QuestionParaphrase
    form_class = ParaphraseForm
    template_name = 'questions/paraphrase_form.html'
    permission_required = 'questions.change_questionparaphrase'

    def dispatch(self, request, *args, **kwargs):
        self.paraphrase_obj = self.get_object()
        self.original_question = self.paraphrase_obj.original_question
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['original_question'] = self.original_question
        context['answers'] = self.original_question.get_answers()
        context['is_create'] = False
        return context

    def form_valid(self, form):
        comment_text = self.request.POST.get('comment', '').strip()

        if not comment_text:
            messages.warning(self.request, 'При сохранении изменений комментарий обязателен.')
            context = self.get_context_data(form=form)
            return self.render_to_response(context)

        paraphrase = form.save()

        history = QuestionHistory.objects.create(
            logical_question=self.original_question,
            entity_type='paraphrase',
            user=self.request.user,
            user_name=self.request.user.get_full_name() or self.request.user.username,
        )
        Action.objects.create(history=history, action_type='updated_field', field_name='question')
        Comment.objects.create(
            history=history,
            user=self.request.user,
            text=comment_text,
            user_name=self.request.user.get_full_name() or self.request.user.username,
        )

        messages.success(self.request, 'Перефраз успешно обновлён.')

        TabView.objects.filter(
            logical_question=self.original_question,
            tab_type='paraphrase',
        ).exclude(user=self.request.user).delete()
        TabView.objects.update_or_create(
            user=self.request.user,
            logical_question=self.original_question,
            tab_type='paraphrase',
            defaults={'viewed_at': timezone.now()}
        )

        # Сброс просмотров основного вопроса
        TabView.objects.filter(
            logical_question=self.original_question,
            tab_type='question',
        ).exclude(user=self.request.user).delete()
        TabView.objects.update_or_create(
            user=self.request.user,
            logical_question=self.original_question,
            tab_type='question',
            defaults={'viewed_at': timezone.now()}
        )

        url = reverse('questions:question_detail', kwargs={'pk': self.original_question.pk})
        return redirect(f'{url}?tab=paraphrase')


class ParaphraseDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = QuestionParaphrase
    permission_required = 'questions.delete_questionparaphrase'

    def get_success_url(self):
        return reverse('questions:question_detail', kwargs={'pk': self.original_question.pk})

    def form_valid(self, form):
        self.original_question = self.object.original_question

        history = QuestionHistory.objects.create(
            logical_question=self.original_question,
            entity_type='paraphrase',
            user=self.request.user,
            user_name=self.request.user.get_full_name() or self.request.user.username,
        )
        Action.objects.create(history=history, action_type='deleted')

        messages.success(self.request, 'Перефраз удалён.')
        response = super().form_valid(form)

        # Сброс просмотров основного вопроса
        TabView.objects.filter(
            logical_question=self.original_question,
            tab_type='question',
        ).exclude(user=self.request.user).delete()
        TabView.objects.update_or_create(
            user=self.request.user,
            logical_question=self.original_question,
            tab_type='question',
            defaults={'viewed_at': timezone.now()}
        )
        return response


class ParaphrasePublishView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'questions.can_publish'

    def post(self, request, pk):
        paraphrase = get_object_or_404(QuestionParaphrase, pk=pk)
        comment_text = request.POST.get('comment', '').strip()

        if not comment_text:
            messages.error(request, 'Комментарий обязателен.')
            return redirect(
                reverse('questions:question_detail', kwargs={'pk': paraphrase.original_question.pk})
                + '?tab=paraphrase'
            )

        if paraphrase.is_published:
            paraphrase.is_published = False
            action_type = 'unpublished'
            msg = 'Перефраз снят с публикации.'
        else:
            paraphrase.is_published = True
            action_type = 'published'
            msg = 'Перефраз опубликован.'

        paraphrase.save()

        history = QuestionHistory.objects.create(
            logical_question=paraphrase.original_question,
            entity_type='paraphrase',
            user=request.user,
            user_name=request.user.get_full_name() or request.user.username,
        )
        Action.objects.create(history=history, action_type=action_type)
        Comment.objects.create(
            history=history,
            user=request.user,
            text=comment_text,
            user_name=request.user.get_full_name() or request.user.username,
        )

        TabView.objects.filter(
            logical_question=paraphrase.original_question,
            tab_type='paraphrase',
        ).exclude(user=request.user).delete()
        TabView.objects.update_or_create(
            user=request.user,
            logical_question=paraphrase.original_question,
            tab_type='paraphrase',
            defaults={'viewed_at': timezone.now()}
        )

        # Сброс просмотров основного вопроса
        TabView.objects.filter(
            logical_question=paraphrase.original_question,
            tab_type='question',
        ).exclude(user=request.user).delete()
        TabView.objects.update_or_create(
            user=request.user,
            logical_question=paraphrase.original_question,
            tab_type='question',
            defaults={'viewed_at': timezone.now()}
        )

        messages.success(request, msg)
        return redirect(
            reverse('questions:question_detail', kwargs={'pk': paraphrase.original_question.pk})
            + '?tab=paraphrase'
        )


class MarkQuestionsViewedView(LoginRequiredMixin, View):
    def post(self, request):
        reset_question_views(request.user)
        messages.success(request, 'Все вопросы отмечены как просмотренные.')
        return redirect(request.META.get('HTTP_REFERER', 'questions:question_list'))


class MarkThemesViewedView(LoginRequiredMixin, View):
    def post(self, request):
        reset_theme_views(request.user)
        messages.success(request, 'Все темы отмечены как просмотренные.')
        return redirect(request.META.get('HTTP_REFERER', 'questions:themes_list'))