from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, View, CreateView, UpdateView, DeleteView, DetailView
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Prefetch
from history.models import QuestionHistory, Comment, Action
from .models import Question, Themes
from core.enums import ACType
from django.contrib import messages
from django.views.generic import TemplateView
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.db.models import Q


class QuestionListView(ListView):
    model = Question
    template_name = 'questions/list.html'
    context_object_name = 'question_list'
    paginate_by = 25

    def get_queryset(self):
        """Применяет фильтры и поиск к queryset."""
        queryset = super().get_queryset().select_related('theme')

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
    template_name = 'questions/detail.html'
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
            return redirect('questions:detail', pk=pk)

        # Получаем комментарий из формы
        comment_text = request.POST.get('comment', '').strip()

        # Проверяем обязательность комментария
        if not comment_text:
            messages.error(request, 'Для изменения статуса вопроса необходимо оставить комментарий.')
            return redirect('questions:detail', pk=pk)



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
        )

        Action.objects.create(
            history=history,
            action_type=action_type,
        )

        # В QuestionPublishView
        Comment.objects.create(
            history=history,
            user=request.user,
            text=comment_text,
        )

        return redirect(f'/questions/{pk}/#head')




