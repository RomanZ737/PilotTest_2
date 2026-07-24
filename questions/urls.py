from django.urls import path
from .views import (
    QuestionListView
)



app_name = 'questions'

urlpatterns = [
    path('list/', QuestionListView.as_view(), name='list'),
]