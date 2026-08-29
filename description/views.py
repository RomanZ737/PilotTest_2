from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import DetailView, UpdateView, RedirectView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from .models import DescriptionPage
from .forms import DescriptionPageForm
from .services import get_available_sections


class DescriptionIndexView(LoginRequiredMixin, RedirectView):
    """Перенаправляем на первый раздел — Права доступа."""
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        sections = get_available_sections(self.request.user)
        if sections.exists():
            return reverse('description:detail', kwargs={'slug': sections.first().slug})
        messages.error(self.request, 'Нет доступных разделов описания.')
        return reverse('core:home')


class DescriptionDetailView(LoginRequiredMixin, DetailView):
    model = DescriptionPage
    template_name = 'description/detail.html'
    context_object_name = 'page'

    # def get_object(self, queryset=None):
    #     page = get_object_or_404(DescriptionPage, slug=self.kwargs['slug'])
    #     # Проверяем доступ
    #     available = get_available_sections(self.request.user)
    #     if not available.filter(pk=page.pk).exists():
    #         messages.error(self.request, 'У вас нет доступа к этому разделу.')
    #         # Редирект на первый доступный раздел
    #         first = available.first()
    #         if first:
    #             return redirect('description:detail', slug=first.slug)
    #         return redirect('core:home')
    #     return page

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sections'] = get_available_sections(self.request.user)
        context['current_slug'] = self.kwargs['slug']
        context['can_edit'] = (
                self.request.user.is_superuser or
                self.request.user.groups.filter(name='Администраторы').exists()
        )
        return context

    def dispatch(self, request, *args, **kwargs):
        available = get_available_sections(request.user)
        if not available.filter(slug=self.kwargs['slug']).exists():
            messages.error(request, 'У вас нет доступа к этому разделу.')
            first = available.first()
            if first:
                return redirect('description:detail', slug=first.slug)
            return redirect('core:home')
        return super().dispatch(request, *args, **kwargs)


class DescriptionUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = DescriptionPage
    form_class = DescriptionPageForm
    template_name = 'description/form.html'
    permission_required = 'description.change_descriptionpage'

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.groups.filter(name='Администраторы').exists()):
            messages.error(request, 'У вас нет прав для редактирования описаний.')
            return redirect('description:detail', slug=self.kwargs['slug'])
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return get_object_or_404(DescriptionPage, slug=self.kwargs['slug'])

    def get_success_url(self):
        return reverse('description:detail', kwargs={'slug': self.object.slug})
