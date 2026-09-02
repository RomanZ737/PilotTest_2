from django.http import JsonResponse
from django.views.generic import RedirectView, ListView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import redirect, render
from django.template.loader import render_to_string


class HomeListView(LoginRequiredMixin, View):

    def get(self, request):
        return render(request, 'core/home.html')


def nav_bar_ajax(request):
    html = render_to_string('core/nav_bar.html', request=request)
    return JsonResponse({'html': html})


