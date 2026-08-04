from django.views.generic import RedirectView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin


class HomeListView(LoginRequiredMixin, RedirectView):
    """Перенаправляет на список вопросов."""
    url = reverse_lazy('questions:question_list')
