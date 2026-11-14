from django.core.management.base import BaseCommand
from core.services.pdf_export import generate_questions_pdf


class Command(BaseCommand):
    help = 'Экспорт базы вопросов в PDF с выделением правильных ответов'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='questions_with_answers.pdf',
            help='Имя файла для сохранения (по умолчанию questions_with_answers.pdf)'
        )

    def handle(self, *args, **options):
        self.stdout.write('Генерация PDF (с ответами)...')

        pdf_buffer = generate_questions_pdf(with_answers=True)

        output_path = options['output']
        with open(output_path, 'wb') as f:
            f.write(pdf_buffer.getvalue())

        self.stdout.write(self.style.SUCCESS(f'PDF успешно сохранён: {output_path}'))