from django.views.generic import RedirectView, ListView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import redirect, render


class HomeListView(LoginRequiredMixin, View):

    def get(self, request):
        return render(request, 'core/home.html')
