from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, View, CreateView, UpdateView, DeleteView, DetailView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from mailing.forms import MailingForm
from mailing.models import Mailing
from recipient.models import Recipient
from .services import update_mailing_status, send_mailing, update_all_mailing_statuses
from django.views.generic import TemplateView
from django.utils import timezone
from django.core.exceptions import PermissionDenied


class PauseMailingView(LoginRequiredMixin, View):
    def post(self, request, pk):
        mailing = get_object_or_404(Mailing, pk=pk)
        if not request.user.groups.filter(name='Managers').exists():
            messages.error(request, 'У вас нет прав для приостановки рассылок.')
            return redirect('mailing:list')

        if mailing.status != 'started' and mailing.status != 'paused':
            messages.warning(request, 'Можно приостановить только запущенную рассылку.')
            return redirect('mailing:list')
        if mailing.status == 'paused':
            new_status = 'started'
            action = 'возобновлена'
        else:
            new_status = 'paused'
            action = 'приостановлена'
        Mailing.objects.filter(pk=mailing.pk).update(status=new_status)
        mailing.status = new_status
        messages.success(request, f'Рассылка "{mailing.message.subject}" приостановлена.')
        return redirect('mailing:list')



class MailingListView(LoginRequiredMixin, ListView):
    model = Mailing
    template_name = 'mailing/mailing_list.html'
    context_object_name = 'mailing_list'

    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name='Managers').exists():
            queryset = Mailing.objects.all()
        else:
            queryset = Mailing.objects.filter(owner=self.request.user)

        update_all_mailing_statuses(queryset)

        return queryset


class MailingCreateView(LoginRequiredMixin, CreateView):
    model = Mailing
    form_class = MailingForm
    template_name = 'mailing/mailing_form.html'
    success_url = reverse_lazy('core:home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.groups.filter(name='Managers').exists():
            recipients = Recipient.objects.all()
        else:
            recipients = Recipient.objects.filter(owner=user)
        context['recipients_list'] = recipients
        context['selected_recipients'] = []  # для создания пусто
        return context

    def form_valid(self, form):
        # Сохраняем рассылку без получателей
        mailing = form.save(commit=False)
        mailing.owner = self.request.user
        mailing.save()
        # Получаем выбранных получателей из POST
        selected_ids = self.request.POST.getlist('recipients')
        mailing.recipients.set(selected_ids)
        return super().form_valid(form)

    def get_initial(self):
        return {'status': 'created'}



class MailingUpdateView(LoginRequiredMixin, UpdateView):
    model = Mailing
    form_class = MailingForm
    template_name = 'mailing/mailing_form.html'
    success_url = reverse_lazy('mailing:list')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.owner != self.request.user:
            raise PermissionDenied("Вы не можете редактировать эту рассылку.")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.groups.filter(name='Managers').exists():
            recipients = Recipient.objects.all()
        else:
            recipients = Recipient.objects.filter(owner=user)
        context['recipients_list'] = recipients
        # Получаем ID уже выбранных получателей для текущей рассылки
        context['selected_recipients'] = self.object.recipients.values_list('id', flat=True)
        return context

    def form_valid(self, form):
        mailing = form.save(commit=False)
        mailing.save()

        selected_ids = self.request.POST.getlist('recipients')
        if not selected_ids:
            form.add_error(None, 'Выберите хотя бы одного получателя.')
            return self.form_invalid(form)
        mailing.recipients.set(selected_ids)
        return super().form_valid(form)


class MailingDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        mailing = get_object_or_404(Mailing, pk=pk)
        # Проверка прав: менеджер или владелец
        if not mailing.owner == request.user:
            messages.error(request, 'У вас нет прав на удаление этой рассылки.')
            return redirect('mailing:list')
        mailing.delete()
        messages.success(request, 'Рассылка успешно удалена.')
        return redirect('mailing:list')



class MailingDetailView(LoginRequiredMixin, DetailView):
    model = Mailing
    template_name = 'mailing/mailing_detail.html'
    context_object_name = 'mailing'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        update_mailing_status(obj)
        return obj



class MailingStartView(LoginRequiredMixin, TemplateView):
    template_name = 'mailing/mailing_start.html'

    def _get_mailing_or_redirect(self, request, pk):
        mailing = get_object_or_404(Mailing, pk=pk)
        now = timezone.now()

        if mailing.owner != request.user:
            messages.error(request, 'У вас нет прав для запуска этой рассылки.')
            return None, redirect('mailing:list')

        if mailing.status == 'paused':
            messages.error(request, 'Рассылка приостановлена менеджером.')
            return None, redirect('mailing:list')

        if not (mailing.start_time <= now <= mailing.end_time):
            messages.error(request, 'Рассылка невозможна. Время рассылки некорректно.')
            return None, redirect('mailing:list')

        return mailing, None

    def get(self, request, pk):
        mailing, error_response = self._get_mailing_or_redirect(request, pk)
        if error_response:
            return error_response
        return self.render_to_response(self.get_context_data(mailing=mailing))

    def post(self, request, pk):
        mailing, error_response = self._get_mailing_or_redirect(request, pk)
        if error_response:
            return error_response

        results = send_mailing(mailing)
        return self.render_to_response(
            self.get_context_data(mailing=mailing, results=results)
        )

# class MailingStartView(LoginRequiredMixin, TemplateView):
#     template_name = 'mailing/mailing_start.html'
#
#     def get(self, request, pk):
#         mailing = get_object_or_404(Mailing, pk=pk)
#         now = timezone.now()
#
#         if not (request.user.groups.filter(name='Managers').exists() or mailing.owner == request.user):
#             messages.error(request, 'У вас нет прав для запуска этой рассылки.')
#             return redirect('mailing:list')
#
#         if not (mailing.start_time <= now <= mailing.end_time):
#             messages.error(request, 'Рассылка невозможна. Время рассылки некорректно.')
#             return redirect('mailing:list')
#
#
#         # Если всё хорошо – показываем страницу с подтверждением
#         context = self.get_context_data(mailing=mailing)
#         return self.render_to_response(context)
#
#     def post(self, request, pk):
#         mailing = get_object_or_404(Mailing, pk=pk)
#
#         # Отправляем письма
#         results = send_mailing(mailing)
#
#         # Обновляем статус, если он ещё не 'finished' (может, уже изменился)
#         if mailing.status == 'started' and mailing.end_time < timezone.now():
#             mailing.status = 'finished'
#             mailing.save(update_fields=['status'])
#
#         # Показываем страницу с результатами
#         context = self.get_context_data(mailing=mailing, results=results)
#         return self.render_to_response(context)





