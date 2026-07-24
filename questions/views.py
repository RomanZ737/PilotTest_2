from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, View, CreateView, UpdateView, DeleteView, DetailView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

from .models import Question

from django.views.generic import TemplateView
from django.utils import timezone
from django.core.exceptions import PermissionDenied


class QuestionListView(ListView):
    model = Question
    template_name = 'questions/list.html'
    context_object_name = 'question_list'