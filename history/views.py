from .models import Comment
from django.views import View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from questions.models import Question
from .models import QuestionHistory
from django.urls import reverse


# Редактирование комментариев (если комментарий последний)
class CommentUpdateView(View):
    def post(self, request, pk):

        print("POST data:", request.POST)  # <-- добавить
        comment_text = request.POST.get('comment', '').strip()
        print("comment_text:", comment_text)  # <-- добавить

        comment = get_object_or_404(Comment, pk=pk)

        # Проверка: комментарий может редактировать только автор
        if comment.user != request.user:
            messages.error(request, 'Вы не можете редактировать этот комментарий.')
            return redirect('questions:detail', pk=comment.history.logical_question.pk)

        # Проверка: комментарий должен быть последним
        last_comment = comment.history.comments.order_by('-created_at').first()
        if comment != last_comment:
            messages.error(request, 'Можно редактировать только последний комментарий.')
            return redirect('questions:detail', pk=comment.history.logical_question.pk)

        # Обновляем текст комментария
        new_text = request.POST.get('comment', '').strip()
        if not new_text:
            messages.error(request, 'Текст комментария не может быть пустым.')
            return redirect('questions:detail', pk=comment.history.logical_question.pk)

        comment.text = new_text
        comment.save()
        messages.success(request, 'Комментарий обновлён.')
        return redirect(f"{reverse('questions:question_detail', kwargs={'pk': comment.history.logical_question.pk})}#history")






class ClearHistoryView(View):
    def post(self, request, question_pk):
        question = get_object_or_404(Question, pk=question_pk)
        count, _ = QuestionHistory.objects.filter(logical_question=question).delete()
        messages.success(request, f'История вопроса #{question_pk} очищена. Удалено записей: {count}.')
        return redirect('questions:question_detail', pk=question_pk)