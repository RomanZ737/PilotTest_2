from django.urls import path
from .views import (
    CommentUpdateView, ClearHistoryView

)
from .apps import HistoryConfig


app_name = HistoryConfig.name

urlpatterns = [

path('comment/update/<int:pk>/', CommentUpdateView.as_view(), name='comment_update'),
path('clear/<int:question_pk>/', ClearHistoryView.as_view(), name='clear_history'),

]