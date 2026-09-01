from django import forms
from .models import Question, Answer, Themes, QuestionDraft, QuestionParaphrase
from django.forms import inlineformset_factory
from django.forms import BaseInlineFormSet, ValidationError
from questions.services import get_user_themes


class ThemeForm(forms.ModelForm):
    class Meta:
        model = Themes
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            available_themes = get_user_themes(user)
            if 'theme' in self.fields:
                self.fields['theme'].queryset = available_themes

    # Проверяем существует ли уже такая тема
    def clean_name(self):
        name = self.cleaned_data.get('name')
        qs = Themes.objects.filter(name=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Тема с таким названием уже существует.')
        return name


class QuestionForm(forms.ModelForm):


    class Meta:
        model = Question
        fields = ['question',
                  'theme',
                  'ac_type',
                  'q_kind',
                  'q_weight',
                  'is_time_limited',
                  'question_img',
                  'comment_img',
                  'comment_text']
        labels = {
            'question': '',
            'theme': 'Тема вопроса',
            'ac_type': 'Тип ВС',
            'q_kind': 'Тип вопроса',
            'q_weight': 'Вес вопроса',
            'is_time_limited': 'Вопрос ограничен по времени ответа',
            'question_img': 'Изображение к вопросу',
            'comment_img': 'Изображение к ответу',
            'comment_text': ''
        }

        widgets = {
            'question': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Введите текст вопроса...'
            }),
            'comment_text': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Пояснение к ответу...'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            available_themes = get_user_themes(user)
            if 'theme' in self.fields:
                self.fields['theme'].queryset = available_themes

    # Проверяем существует ли уже такой вопрос
    def clean_question(self):
        question = self.cleaned_data.get('question')
        qs = Question.objects.filter(question=question, is_archived=False)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Вопрос с таким текстом уже существует.')
        return question


class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ['answer',]
        labels = {
            'answer': 'Ответ'
        }


class AnswerFormSet(BaseInlineFormSet):
    def clean(self):
        print('DEBUG AnswerFormSet.clean вызван')
        super().clean()
        print(f'DEBUG: errors after super: {self.errors}')

        if any(self.errors):
            print('DEBUG: есть ошибки, выхожу')
            return

        answers = []
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                print(f'DEBUG form data: answer={form.cleaned_data.get("answer")}, is_correct={form.cleaned_data.get("is_correct")}')
                answers.append(form.cleaned_data)

        correct_count = sum(1 for a in answers if a.get('is_correct'))
        q_kind = self.data.get('q_kind')
        print(f'DEBUG: correct_count={correct_count}, q_kind={q_kind}')

        if correct_count == 0:
            print('DEBUG: нет правильных ответов')
            raise ValidationError('Хотя бы один ответ должен быть правильным.')

        if q_kind == 'SINGLE' and correct_count != 1:
            print('DEBUG: SINGLE ошибка')
            raise ValidationError(
                'Для вопроса с одним правильным ответом должен быть выбран ровно один правильный вариант.')

        if q_kind == 'MULTY' and correct_count < 2:
            print('DEBUG: MULTY ошибка')
            raise ValidationError(
                'Для вопроса с несколькими правильными ответами должно быть выбрано минимум два правильных варианта.')

        print('DEBUG: clean прошёл успешно')


AnswerFormSetFactory = inlineformset_factory(
    Question,
    Answer,
    form=AnswerForm,
    formset=AnswerFormSet,
    fields=['answer', 'is_correct'],
    extra=2,
    max_num=10,
    #min_num=2,
    validate_min=True,
    can_delete=True,  # чтобы можно было удалять пустые строки
)


class DraftForm(forms.ModelForm):
    class Meta:
        model = QuestionDraft
        fields = [
            'question', 'theme', 'ac_type', 'q_kind', 'q_weight',
            'is_time_limited', 'question_img', 'comment_img', 'comment_text'
        ]
        labels = {
            'question': '',
            'theme': 'Тема вопроса',
            'ac_type': 'Тип ВС',
            'q_kind': 'Тип вопроса',
            'q_weight': 'Вес вопроса',
            'is_time_limited': 'Вопрос ограничен по времени ответа',
            'question_img': 'Изображение к вопросу',
            'comment_img': 'Изображение к ответу',
            'comment_text': '',
        }
        widgets = {
            'question': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Введите текст вопроса...'
            }),
            'comment_text': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Пояснение к ответу...'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            available_themes = get_user_themes(user)
            if 'theme' in self.fields:
                self.fields['theme'].queryset = available_themes

    def clean_question(self):
        question = self.cleaned_data.get('question')
        qs = Question.objects.filter(question=question, is_archived=False)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.original_question.pk)
        if qs.exists():
            raise ValidationError('Вопрос с таким текстом уже существует.')
        return question


DraftAnswerFormSetFactory = inlineformset_factory(
    QuestionDraft,
    Answer,
    form=AnswerForm,
    formset=AnswerFormSet,
    fields=['answer', 'is_correct'],
    extra=0,
    max_num=10,
    can_delete=True,
)


class ParaphraseForm(forms.ModelForm):
    """Форма для создания и редактирования перефраза."""

    class Meta:
        model = QuestionParaphrase
        fields = [
            'question',
            'theme',
            'ac_type',
            'q_kind',
            'q_weight',
            'is_time_limited',
        ]
        widgets = {
            'question': forms.Textarea(attrs={
                'rows': 5,
                'class': 'form-control',
                'placeholder': 'Введите перефразированный текст вопроса...',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Все поля кроме question делаем readonly
        readonly_fields = ['theme', 'ac_type', 'q_kind', 'q_weight', 'is_time_limited']
        for field_name in readonly_fields:
            if field_name in self.fields:
                self.fields[field_name].disabled = True
                self.fields[field_name].required = False