from django.urls import path
from .views import (
    QuestionListView,
    QuestionDetailView,
    QuestionPublishView,
    QuestionCreateView,
    ThemesListView,
    ThemesCreateView,
    ThemesDetailView,
    ThemesUpdateView,
    ThemesDeleteView,
    QuestionDeleteView,
    DraftUpdateView,
    DraftCreateView,
    DraftPublishView,
    DraftDeleteView,
    ArchiveRestoreView,
    ParaphraseCreateView,
    ParaphraseUpdateView,
    ParaphraseDeleteView,
    ParaphrasePublishView
)
from .apps import QuestionsConfig


app_name = QuestionsConfig.name

urlpatterns = [
    path('', QuestionListView.as_view(), name='question_list'),
    path('question/create/', QuestionCreateView.as_view(), name='question_create'),
    path('question/<int:pk>/', QuestionDetailView.as_view(), name='question_detail'),
    path('question/<int:pk>/delete/', QuestionDeleteView.as_view(), name='question_delete'),
    path('themes/', ThemesListView.as_view(), name='themes_list'),
    path('themes/create/', ThemesCreateView.as_view(), name='theme_create'),
    path('themes/<int:pk>/', ThemesDetailView.as_view(), name='themes_detail'),
    path('themes/<int:pk>/update/', ThemesUpdateView.as_view(), name='theme_update'),
    path('themes/<int:pk>/delete/', ThemesDeleteView.as_view(), name='theme_delete'),
    path('publish/<int:pk>/', QuestionPublishView.as_view(), name='publish'),
    path('draft/<int:pk>/edit/', DraftUpdateView.as_view(), name='draft_edit'),
    path('question/<int:pk>/draft/create/', DraftCreateView.as_view(), name='draft_create'),
    path('draft/<int:pk>/publish/', DraftPublishView.as_view(), name='draft_publish'),
    path('draft/<int:pk>/delete/', DraftDeleteView.as_view(), name='draft_delete'),
    path('question/<int:pk>/restore/', ArchiveRestoreView.as_view(), name='archive_restore'),
    path('paraphrase/<int:pk>/create/', ParaphraseCreateView.as_view(), name='paraphrase_create'),
    path('paraphrase/<int:pk>/update/', ParaphraseUpdateView.as_view(), name='paraphrase_update'),
    path('paraphrase/<int:pk>/delete/', ParaphraseDeleteView.as_view(), name='paraphrase_delete'),
    path('paraphrase/<int:pk>/publish/', ParaphrasePublishView.as_view(), name='paraphrase_publish'),
]