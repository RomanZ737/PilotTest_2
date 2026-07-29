from django.urls import path
from .views import (
    QuestionListView,
    QuestionDetailView,
    QuestionPublishView,

)
from .apps import QuestionsConfig


app_name = QuestionsConfig.name

urlpatterns = [
    path('', QuestionListView.as_view(), name='list'),
    path('<int:pk>/', QuestionDetailView.as_view(), name='detail'),
    path('publish/<int:pk>/', QuestionPublishView.as_view(), name='publish'),
]