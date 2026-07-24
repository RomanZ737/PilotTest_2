from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, View, CreateView, UpdateView, DeleteView
from django.utils import timezone
from django.core.cache import cache



class HomeListView(LoginRequiredMixin, ListView):
    model = Mailing
    template_name = 'core/home.html'
    context_object_name = 'mailings'

    def _is_manager(self):
        return self.request.user.groups.filter(name='Managers').exists()

    def get_queryset(self):
        user = self.request.user
        cache_key = f'active_mailings_user_{user.id}'
        queryset = cache.get(cache_key)
        if queryset is None:
            now = timezone.now()
            if self._is_manager():
                queryset = Mailing.objects.filter(
                    status='started',
                    start_time__lte=now,
                    end_time__gte=now
                )
            else:
                queryset = Mailing.objects.filter(
                    status='started',
                    start_time__lte=now,
                    end_time__gte=now,
                    owner=user
                )
            cache.set(cache_key, queryset, 60 * 5)  # 5 минут
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        # Кэшируем статистику отдельно
        stats_key = f'home_stats_user_{user.id}'
        stats = cache.get(stats_key)
        if stats is None:
            if self._is_manager():
                total_mailing = Mailing.objects.count()
                total_recipients = Recipient.objects.count()
            else:
                total_mailing = Mailing.objects.filter(owner=user).count()
                total_recipients = Recipient.objects.filter(owner=user).count()
            stats = {
                'total_mailing_number': total_mailing,
                'total_recipients_number': total_recipients,
            }
            cache.set(stats_key, stats, 60 * 10)  # 10 минут
        context['total_mailing_number'] = stats['total_mailing_number']
        context['total_recipients_number'] = stats['total_recipients_number']
        return context





