from django.urls import path
from .views import (
    MailingListView,
    MailingCreateView,
    MailingUpdateView,
    MailingDeleteView,
    MailingDetailView,
    MailingStartView,
    PauseMailingView
)



app_name = 'mailing'

urlpatterns = [
    path('mailing/<int:pk>/pause/', PauseMailingView.as_view(), name='pause'),
    path('list/', MailingListView.as_view(), name='list'),
    path('create/', MailingCreateView.as_view(), name='create'),
    path('<int:pk>/update', MailingUpdateView.as_view(), name='update'),
    path('<int:pk>/delete', MailingDeleteView.as_view(), name='delete'),
    path('<int:pk>/detail', MailingDetailView.as_view(), name='detail'),
    path('<int:pk>/start', MailingStartView.as_view(), name='start'),
]