from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, View, CreateView, UpdateView, DeleteView, DetailView
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Prefetch
from history.models import QuestionHistory, Comment, Action, DraftView
from .forms import QuestionForm, AnswerFormSetFactory, ThemeForm, DraftForm, DraftAnswerFormSetFactory
from .models import Question, Themes, Answer, QuestionDraft
from core.enums import ACType
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.http import HttpResponseRedirect
from django.urls import reverse



class QuestionListView(ListView):
    model = Question
    template_name = 'questions/list.html'
    context_object_name = 'question_list'
    paginate_by = 25

    def get_queryset(self):
        """Применяет фильтры и поиск к queryset."""
        queryset = super().get_queryset().select_related('theme')
        queryset = queryset.filter(is_archived=False)

        # Поиск по тексту вопроса
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(question__icontains=search)

        # Фильтр по теме
        theme_id = self.request.GET.get('theme')
        if theme_id:
            queryset = queryset.filter(theme_id=theme_id)

        # Фильтр по типу ВС
        ac_type = self.request.GET.get('ac_type')
        if ac_type:
            queryset = queryset.filter(ac_type=ac_type)

        # Фильтр по статусу (опубликован / черновик)
        status = self.request.GET.get('status')
        if status == 'published':
            queryset = queryset.filter(is_published=True)
        elif status == 'draft':
            queryset = queryset.filter(is_published=False)

        # Сортировка (можно добавить параметр, но пока по умолчанию)
        return queryset.order_by('theme__name', 'question')

    def get_context_data(self, **kwargs):
        """Добавляет в контекст данные для фильтров и текущие параметры."""
        context = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        if 'page' in params:
            params.pop('page')
        context['query_string'] = params.urlencode()
        # Список всех тем для выпадающего списка
        context['themes'] = Themes.objects.all().order_by('name')
        # Варианты типов ВС (из enums)
        context['ac_type_choices'] = ACType.choices
        # Текущие GET-параметры (чтобы сохранять их при переключении страниц)
        context['current_filters'] = self.request.GET.copy()
        return context


class QuestionDetailView(DetailView):
    model = Question
    template_name = 'questions/question_detail.html'
    context_object_name = 'question'

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

        # Черновик
        draft = question.drafts.order_by('-updated_at').first()
        if draft:
            context['draft'] = draft
            if self.request.user.is_authenticated:
                context['draft'].is_new = not draft.views.filter(
                    user=self.request.user
                ).exists()

        # Перефразировки
        context['paraphrases'] = question.paraphrases.filter(is_published=True)

        # История с фильтрацией и сортировкой
        history_qs = question.history.all()

        # Фильтрация по пользователю
        user_filter = self.request.GET.get('user')
        if user_filter:
            history_qs = history_qs.filter(
                Q(user__username__icontains=user_filter) |
                Q(user__first_name__icontains=user_filter) |
                Q(user__last_name__icontains=user_filter) |
                Q(user__email__icontains=user_filter)
            )

        # Фильтрация по действию
        action_filter = self.request.GET.get('action')
        if action_filter and action_filter != 'all':
            history_qs = history_qs.filter(actions__action_type=action_filter).distinct()

        # Сортировка
        sort = self.request.GET.get('sort', 'date_desc')
        if sort == 'date_asc':
            history_qs = history_qs.order_by('created_at')
        else:  # date_desc
            history_qs = history_qs.order_by('-created_at')

        context['history'] = history_qs

        # ПОСЛЕДНИЙ КОММЕНТАРИЙ ВО ВСЕЙ ИСТОРИИ ВОПРОСА
        context['last_comment'] = Comment.objects.filter(
            history__logical_question=question
        ).order_by('-created_at').first()

        return context


class QuestionPublishView(View):

    def post(self, request, pk):
        question = get_object_or_404(Question, pk=pk)

        if question.is_archived:
            messages.error(request, 'Нельзя изменить статус архивного вопроса.')
            return redirect('questions:question_list')

        # Получаем комментарий из формы
        comment_text = request.POST.get('comment', '').strip()

        # Проверяем обязательность комментария
        if not comment_text:
            messages.error(request, 'Для изменения статуса вопроса необходимо оставить комментарий.')
            redirect_to = request.POST.get('redirect_to', '')
            if redirect_to == 'list':
                return redirect('questions:question_list')
            return redirect('questions:question_detail', pk=pk)

        if question.is_published:
            question.is_published = False
            action_type = 'unpublished'
            messages.warning(request, f'Вопрос снят с публикации и НЕ будет использован в тестах.')
        else:
            question.is_published = True
            question.published_at = timezone.now()
            action_type = 'published'
            messages.success(request, f'Вопрос опубликован и будет использовать в тестах.')
        question.save()

        # --- Запись в историю ---
        history = QuestionHistory.objects.create(
            logical_question=question,
            entity_type='question',
            user=request.user,
            user_name=request.user.get_full_name() or request.user.username
        )

        Action.objects.create(
            history=history,
            action_type=action_type,
        )

        Comment.objects.create(
            history=history,
            user=request.user,
            user_name=request.user.get_full_name() or request.user.username,
            text=comment_text,
        )

        # Редирект в зависимости от источника
        redirect_to = request.POST.get('redirect_to', '')
        if redirect_to == 'list':
            return redirect('questions:question_list')
        return redirect('questions:question_detail', pk=question.pk)


class QuestionCreateView(CreateView):
    model = Question
    form_class = QuestionForm
    template_name = 'questions/question_form.html'

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


        # Сохраняем ответы с автоматическим answer_order
        answer_formset.instance = self.object
        answers = answer_formset.save(commit=False)
        for i, answer in enumerate(answers, start=1):
            answer.answer_order = i
            answer.save()

        # Удаляем помеченные на удаление
        for obj in answer_formset.deleted_objects:
            obj.delete()
        request = self.request
        # Запись в историю
        history = QuestionHistory.objects.create(
            logical_question=self.object,
            entity_type='question',
            user=self.request.user,
            user_name=request.user.get_full_name() or request.user.username
        )
        Action.objects.create(history=history, action_type='created')

        messages.success(self.request, f'Вопрос #{self.object.pk} успешно создан.')
        return redirect('questions:question_detail', pk=self.object.pk)

    def form_invalid(self, form):
        context = self.get_context_data()
        return self.render_to_response(context)

class QuestionDeleteView(View):
    def post(self, request, pk):
        question = get_object_or_404(Question, pk=pk)
        question.delete()
        messages.success(request, f'Вопрос #{pk} удалён.')
        return redirect('questions:question_list')

class ThemesListView(ListView):
    model = Themes
    template_name = 'questions/themes_list.html'
    context_object_name = 'themes_list'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        if 'page' in params:
            params.pop('page')
        context['query_string'] = params.urlencode()
        return context
    
class ThemesDetailView(DetailView):
    model = Themes
    template_name = 'questions/theme_detail.html'
    context_object_name = 'theme'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        theme = self.get_object()
        context['question_count'] = theme.question_set.count()
        return context


class ThemesUpdateView(UpdateView):
    model = Themes
    form_class = ThemeForm
    template_name = 'questions/theme_form.html'
    success_url = reverse_lazy('questions:themes_list')


class ThemesDeleteView(View):
    def post(self, request, pk):
        theme = get_object_or_404(Themes, pk=pk)
        theme.delete()
        messages.success(request, f'Тема #{pk} удалён.')
        return redirect('questions:themes_list')


class ThemesCreateView(CreateView):
    model = Themes
    form_class = ThemeForm
    template_name = 'questions/theme_form.html'
    success_url = reverse_lazy('questions:themes_list')

    def form_valid(self, form):
        self.object = form.save()

        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'id': self.object.id,
                'name': self.object.name,
            })

        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Рендерим форму с ошибками и возвращаем HTML
            html = render_to_string(
                'questions/includes/theme_modal_form.html',
                {'form': form},
                request=self.request
            )
            return JsonResponse({'success': False, 'html': html})

        return super().form_invalid(form)


class DraftCreateView(View):
    def post(self, request, pk):
        question = get_object_or_404(Question, pk=pk)

        # Проверяем, что нет активного черновика
        if question.drafts.exists():
            draft = question.drafts.first()
            messages.warning(request, 'Черновик уже существует.')
            return redirect('questions:question_detail', pk=pk)

        # Создаём черновик — копия вопроса
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

        # Копируем ответы
        for answer in question.answers.all():
            Answer.objects.create(
                question_draft=draft,
                answer=answer.answer,
                is_correct=answer.is_correct,
                answer_order=answer.answer_order,
            )

        # Запись в историю
        history = QuestionHistory.objects.create(
            logical_question=question,
            entity_type='draft',
            user=request.user,
            user_name=request.user.get_full_name() or request.user.username,
        )
        Action.objects.create(history=history, action_type='created')

        DraftView.objects.create(
            user=request.user,
            draft=draft,
        )

        messages.success(request, 'Черновик создан.')
        return redirect('questions:draft_edit', pk=draft.pk)


class DraftUpdateView(UpdateView):
    model = QuestionDraft
    form_class = DraftForm
    template_name = 'questions/draft_form.html'

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

        # Проверяем, были ли изменения
        has_changes = form.has_changed()
        if not has_changes:
            # Проверяем изменения в ответах
            for answer_form in answer_formset:
                if answer_form.has_changed():
                    has_changes = True
                    break
            # Проверяем добавленные ответы (есть формы с id=None и не DELETE)
            for answer_form in answer_formset.forms:
                if not answer_form.cleaned_data.get('id') and not answer_form.cleaned_data.get('DELETE', False):
                    has_changes = True
                    break
            # Проверяем удалённые ответы
            if any(answer_form.cleaned_data.get('DELETE', False) for answer_form in answer_formset.forms if
                   answer_form.cleaned_data):
                has_changes = True

        # Если изменения есть — комментарий обязателен
        comment_text = self.request.POST.get('comment', '').strip()
        if has_changes and not comment_text:
            messages.warning(self.request, 'При сохранении изменений комментарий обязателен.')
            return self.render_to_response(context)

        # Сохраняем
        self.object = form.save()
        answer_formset.instance = self.object
        answers = answer_formset.save(commit=False)
        for i, answer in enumerate(answers, start=1):
            answer.answer_order = i
            answer.save()
        for obj in answer_formset.deleted_objects:
            obj.delete()

        # Запись в историю только если были изменения
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

        url = reverse('questions:question_detail', kwargs={'pk': self.object.original_question.pk})
        return redirect(f'{url}?tab=draft')


class DraftPublishView(View):
    def post(self, request, pk):
        draft = get_object_or_404(QuestionDraft, pk=pk)
        original = draft.original_question

        # Удаляем предыдущую архивную версию, если есть
        if original.previous_version:
            original.previous_version.delete()

        # Создаём архивную копию старого вопроса
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

        # Копируем старые ответы в архив
        for answer in original.answers.all():
            Answer.objects.create(
                question=archived,
                answer=answer.answer,
                is_correct=answer.is_correct,
                answer_order=answer.answer_order,
            )

        # Переносим данные из черновика в оригинальный вопрос
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

        # Удаляем старые ответы оригинала и копируем из черновика
        original.answers.all().delete()
        for draft_answer in draft.answers.all():
            Answer.objects.create(
                question=original,
                answer=draft_answer.answer,
                is_correct=draft_answer.is_correct,
                answer_order=draft_answer.answer_order,
            )

        # Удаляем черновик
        draft.delete()

        # Запись в историю
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

        messages.success(request, 'Черновик опубликован.')
        return redirect('questions:question_detail', pk=original.pk)


class DraftDeleteView(View):
    def post(self, request, pk):
        draft = get_object_or_404(QuestionDraft, pk=pk)
        question_pk = draft.original_question.pk

        # Запись в историю
        history = QuestionHistory.objects.create(
            logical_question=draft.original_question,
            entity_type='draft',
            user=request.user,
            user_name=request.user.get_full_name() or request.user.username,
        )
        Action.objects.create(history=history, action_type='deleted')

        draft.delete()
        messages.success(request, 'Черновик удалён.')
        return redirect('questions:question_detail', pk=question_pk)


class ArchiveRestoreView(View):
    def post(self, request, pk):
        question = get_object_or_404(Question, pk=pk)
        archived = question.previous_version

        # Сохраняем данные текущего вопроса для черновика
        draft_question = question.question
        draft_theme = question.theme
        draft_ac_type = question.ac_type
        draft_q_kind = question.q_kind
        draft_q_weight = question.q_weight
        draft_is_time_limited = question.is_time_limited
        draft_question_img = question.question_img
        draft_comment_img = question.comment_img
        draft_comment_text = question.comment_text

        # Переносим данные из архива в текущий вопрос
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

        # Создаём черновик из старых данных текущего вопроса
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

        # Переносим старые ответы в черновик, удаляем из вопроса
        for answer in question.answers.all():
            Answer.objects.create(
                question_draft=draft,
                answer=answer.answer,
                is_correct=answer.is_correct,
                answer_order=answer.answer_order,
            )
        question.answers.all().delete()

        # Копируем ответы из архива в текущий вопрос
        for archived_answer in archived.answers.all():
            Answer.objects.create(
                question=question,
                answer=archived_answer.answer,
                is_correct=archived_answer.is_correct,
                answer_order=archived_answer.answer_order,
            )

        # Удаляем архивную версию
        archived.delete()

        # История
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

        messages.success(request, 'Архивная версия восстановлена. Текущая версия сохранена как черновик.')
        return redirect('questions:question_detail', pk=question.pk)