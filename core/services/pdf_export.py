import io
import html
from django.conf import settings
from django.utils.html import strip_tags
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def get_pdf_styles():
    styles = getSampleStyleSheet()

    # Регистрация шрифта с поддержкой кириллицы
    font_path = settings.BASE_DIR / 'static' / 'fonts' / 'DejaVuSans.ttf'
    font_bold_path = settings.BASE_DIR / 'static' / 'fonts' / 'DejaVuSans-Bold.ttf'

    try:
        pdfmetrics.registerFont(TTFont('AppFont', str(font_path)))
        pdfmetrics.registerFont(TTFont('AppFont-Bold', str(font_bold_path)))
        font_name = 'AppFont'
        font_bold = 'AppFont-Bold'
    except Exception:
        font_name = 'Helvetica'
        font_bold = 'Helvetica-Bold'

    styles.add(ParagraphStyle(
        name='TitleStyle',
        parent=styles['Heading1'],
        fontName=font_bold,
        fontSize=18,
        spaceAfter=20,
        alignment=1,  # Center
    ))
    styles.add(ParagraphStyle(
        name='MetaStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        textColor=colors.gray,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name='QuestionStyle',
        parent=styles['Normal'],
        fontName=font_bold,
        fontSize=12,
        spaceAfter=10,
        leading=15,
    ))
    styles.add(ParagraphStyle(
        name='OptionStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=11,
        leading=15,
        leftIndent=20,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name='CorrectOptionStyle',
        parent=styles['OptionStyle'],
        fontName=font_bold,
        textColor=colors.green,
    ))
    styles.add(ParagraphStyle(
        name='CommentStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        textColor=colors.HexColor('#555555'),
        spaceBefore=6,
        spaceAfter=10,
        leading=13,
    ))
    return styles


def clean_html(text):
    """Очищает текст от HTML-тегов (TinyMCE) и декодирует сущности."""
    if not text:
        return ''
    return html.unescape(strip_tags(text))


def generate_questions_pdf(with_answers: bool) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = get_pdf_styles()
    story = []

    # Заголовок документа
    title = "База вопросов (с ответами)" if with_answers else "База вопросов (без ответов)"
    story.append(Paragraph(title, styles['TitleStyle']))

    # Выгружаем только активные (не архивные) вопросы
    from questions.models import Question
    questions = Question.objects.filter(is_archived=False).select_related('theme').prefetch_related('answers')

    for idx, q in enumerate(questions, start=1):
        # Мета-информация
        meta_text = (
            f"ID: {q.id} | Тема: {q.theme.name} | "
            f"Тип ВС: {q.get_ac_type_display()} | "
            f"Тип: {q.get_q_kind_display()}"
        )
        story.append(Paragraph(meta_text, styles['MetaStyle']))

        # Текст вопроса
        story.append(Paragraph(f"{idx}. {clean_html(q.question)}", styles['QuestionStyle']))

        # Варианты ответов
        answers = q.get_answers()
        for i, ans in enumerate(answers, start=1):
            option_text = f"{i}) {clean_html(ans.answer)}"
            if with_answers and ans.is_correct:
                # Выделяем правильные ответы жирным и зеленым цветом
                story.append(Paragraph(f"<b>[✓] {option_text}</b>", styles['CorrectOptionStyle']))
            else:
                story.append(Paragraph(option_text, styles['OptionStyle']))

        # Пояснение к ответу (если есть)
        if q.comment_text:
            story.append(Paragraph(f"<i>Пояснение: {clean_html(q.comment_text)}</i>", styles['CommentStyle']))

        # Отступ между вопросами
        story.append(Spacer(1, 25))

    doc.build(story)
    buffer.seek(0)
    return buffer