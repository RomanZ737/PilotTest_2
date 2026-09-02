from django.http import JsonResponse
from django.views.generic import RedirectView, ListView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import redirect, render
from django.template.loader import render_to_string


class HomeListView(LoginRequiredMixin, View):

    def get(self, request):
        return render(request, 'core/home.html')


def notification_flags_ajax(request):
    from core.context_processors import unread_notifications
    data = unread_notifications(request)
    return JsonResponse({
        'new_questions_exist': data.get('new_questions_exist', False),
        'new_themes_exist': data.get('new_themes_exist', False),
        'history_has_new': data.get('history_has_new', False),
        'new_questions_count': data.get('new_questions_count', False),
        'new_users_count': data.get('new_users_count', 0),
    })


