from django.contrib import admin
from .models import Question


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('theme', 'question',
                    'ac_type', 'is_published',
                    'published_at', 'updated_at',
                    'q_kind', 'q_weight', 'is_time_limited',
                    'question_img', 'comment_img',
                    'comment_text')
    list_filter = ('theme', 'ac_type', 'is_published', 'q_kind')
    search_fields = ('theme', 'question')
