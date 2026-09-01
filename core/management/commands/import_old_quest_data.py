import shutil
from pathlib import Path
import pymysql
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from questions.models import Question, Answer, Themes
from core.enums import ACType


class Command(BaseCommand):
    help = 'Импорт данных из старой MySQL базы (raw SQL) с переносом изображений (через pymysql)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--old-db',
            type=str,
            default='old_db',
            help='Имя соединения с БД в settings.py (по умолчанию "old_db")'
        )
        parser.add_argument(
            '--old-media-root',
            type=str,
            default=str(settings.BASE_DIR / 'media_old'),
            help='Путь к папке со старыми медиа (по умолчанию BASE_DIR/media_old)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Ограничить количество импортируемых записей (для теста)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Пробный запуск без сохранения в БД и без копирования файлов'
        )

    def handle(self, *args, **options):
        self.old_db = options['old_db']
        self.old_media_root = Path(options['old_media_root'])
        self.limit = options['limit']
        self.dry_run = options['dry_run']

        self.stdout.write(self.style.SUCCESS(f'🚀 Импорт из БД: {self.old_db}'))
        self.stdout.write(f'📁 Старые медиа: {self.old_media_root}')
        if self.dry_run:
            self.stdout.write(self.style.WARNING('⚠️  Режим DRY-RUN – данные НЕ будут сохранены, файлы НЕ будут скопированы'))

        if not self.dry_run and not self.old_media_root.exists():
            self.stdout.write(self.style.WARNING(
                f'⚠️  Папка со старыми медиа не найдена: {self.old_media_root}\n'
                'Изображения не будут скопированы, но импорт данных продолжится.'
            ))

        try:
            self.get_old_data("SELECT 1")
        except Exception as e:
            raise CommandError(f'Не удалось подключиться к старой БД: {e}')

        if not self.dry_run:
            transaction.set_autocommit(False)

        try:
            self.import_data()
            if not self.dry_run:
                transaction.commit()
                self.stdout.write(self.style.SUCCESS('✅ Импорт успешно завершён!'))
        except Exception as e:
            if not self.dry_run:
                transaction.rollback()
            self.stdout.write(self.style.ERROR(f'❌ Ошибка: {e}'))
            raise CommandError(f'Импорт прерван: {e}')
        finally:
            if not self.dry_run:
                transaction.set_autocommit(True)

    def get_old_data(self, query, params=None):
        db_settings = settings.DATABASES[self.old_db]
        conn = pymysql.connect(
            host=db_settings['HOST'],
            user=db_settings['USER'],
            password=db_settings['PASSWORD'],
            database=db_settings['NAME'],
            port=int(db_settings['PORT']),
            charset='utf8mb4',
        )
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(query, params or [])
                return cursor.fetchall()
        finally:
            conn.close()

    def safe_strip(self, value):
        """Безопасное преобразование в строку и удаление пробелов."""
        if value is None:
            return ''
        return str(value).strip()

    def import_data(self):
        query = """
            SELECT 
                qs.id AS old_id,
                qs.question,
                qs.question_img,
                qs.option_1,
                qs.option_2,
                qs.option_3,
                qs.option_4,
                qs.option_5,
                qs.option_6,
                qs.option_7,
                qs.option_8,
                qs.option_9,
                qs.option_10,
                qs.comment_img,
                qs.comment_text,
                qs.q_kind,
                qs.q_weight,
                qs.answer,
                qs.answers,
                qs.ac_type,
                qs.is_active,
                qs.is_for_center,
                qs.is_timelimited,
                t.name AS theme_name
            FROM quize737_questionset qs
            LEFT JOIN quize737_thems t ON qs.them_name_id = t.id
            WHERE qs.is_active = 1
        """
        if self.limit:
            query += f" LIMIT {self.limit}"

        old_records = self.get_old_data(query)

        total = len(old_records)
        self.stdout.write(f'📊 Найдено записей для импорта: {total}')
        if total == 0:
            self.stdout.write(self.style.WARNING('Нет записей для импорта'))
            return

        theme_cache = {}
        created_questions = 0
        created_answers = 0
        copied_images = 0
        skipped_images = 0
        skipped_questions = 0

        for idx, old in enumerate(old_records, start=1):
            question_text = self.safe_strip(old.get('question'))
            self.stdout.write(f'Обработка {idx}/{total}: {question_text[:50]}...')

            theme_name = self.safe_strip(old.get('theme_name'))
            if not theme_name:
                self.stdout.write(self.style.WARNING(f'  ⚠️  Пропущен вопрос без темы: {question_text[:50]}'))
                skipped_questions += 1
                continue

            if theme_name not in theme_cache:
                theme, created = Themes.objects.get_or_create(
                    name=theme_name,
                    defaults={'description': ''}
                )
                theme_cache[theme_name] = theme
                if created:
                    self.stdout.write(f'  ✅ Создана новая тема: {theme_name}')
            else:
                theme = theme_cache[theme_name]

            ac_type_value = self.safe_strip(old.get('ac_type')) or 'ANY'
            if ac_type_value not in dict(ACType.choices):
                ac_type_value = 'ANY'

            question = Question(
                question=question_text,
                theme=theme,
                ac_type=ac_type_value,
                q_kind=bool(old.get('q_kind', False)),
                q_weight=float(old.get('q_weight', 0.0) or 0.0),
                is_time_limited=bool(old.get('is_timelimited', False)),
                is_published=bool(old.get('is_active', False)),
                is_draft=not bool(old.get('is_active', False)),
                is_paraphrased=False,
                published_at=timezone.now(),
            )

            # Безопасная обработка изображений
            old_q_img = self.safe_strip(old.get('question_img'))
            if old_q_img:
                new_q_img = self.copy_image(old_q_img, 'questions/img/', old['old_id'])
                question.question_img = new_q_img
                if new_q_img:
                    copied_images += 1
                else:
                    skipped_images += 1

            old_c_img = self.safe_strip(old.get('comment_img'))
            if old_c_img:
                new_c_img = self.copy_image(old_c_img, 'questions/comments/', old['old_id'])
                question.comment_img = new_c_img
                if new_c_img:
                    copied_images += 1
                else:
                    skipped_images += 1

            question.comment_text = self.safe_strip(old.get('comment_text'))

            # Сбор вариантов ответов
            options = []
            for i in range(1, 11):
                opt = self.safe_strip(old.get(f'option_{i}'))
                if opt:
                    options.append((i, opt))

            if not options:
                self.stdout.write(self.style.WARNING(f'  ⚠️  Вопрос без вариантов ответа: {question_text[:50]}'))
                skipped_questions += 1
                continue

            # Определение правильных ответов
            correct_numbers = set()
            q_kind = bool(old.get('q_kind', False))

            if not q_kind:
                correct_num = old.get('answer')
                if correct_num is not None and 1 <= correct_num <= 10:
                    correct_numbers.add(correct_num)
                else:
                    self.stdout.write(self.style.WARNING(
                        f'  ⚠️  Неверный номер правильного ответа ({correct_num}) для вопроса: {question_text[:50]}'
                    ))
            else:
                answers_str = self.safe_strip(old.get('answers'))
                if answers_str:
                    for part in answers_str.split(','):
                        try:
                            num = int(self.safe_strip(part))
                            if 1 <= num <= 10:
                                correct_numbers.add(num)
                        except ValueError:
                            pass
                if not correct_numbers:
                    self.stdout.write(self.style.WARNING(
                        f'  ⚠️  Нет правильных ответов для вопроса с q_kind=True: {question_text[:50]}'
                    ))

            if not self.dry_run:
                question.save()
                created_questions += 1
            else:
                question.id = idx

            for num, text in options:
                is_correct = num in correct_numbers
                if not self.dry_run:
                    Answer.objects.create(
                        question=question,
                        answer=text,
                        is_correct=is_correct,
                        answer_order=num,
                    )
                    created_answers += 1
                else:
                    self.stdout.write(f'    🔍 Ответ {num}: {text[:30]}... {"(правильный)" if is_correct else ""}')

        self.stdout.write(self.style.SUCCESS(
            f'\n📊 ИТОГО:\n'
            f'  - Создано вопросов: {created_questions}\n'
            f'  - Создано ответов: {created_answers}\n'
            f'  - Скопировано изображений: {copied_images}\n'
            f'  - Пропущено изображений (не найдены): {skipped_images}\n'
            f'  - Пропущено вопросов (ошибки): {skipped_questions}\n'
        ))

    def copy_image(self, old_relative_path, new_subdir, old_id):
        if self.dry_run:
            return old_relative_path

        if not self.old_media_root.exists():
            return ''

        old_file = self.old_media_root / old_relative_path
        if not old_file.exists():
            self.stdout.write(self.style.WARNING(f'    ⚠️  Файл не найден: {old_file}'))
            return ''

        filename = old_file.name
        new_filename = f"{old_id}_{filename}"
        new_relative = Path(new_subdir) / new_filename
        new_full = settings.MEDIA_ROOT / new_relative

        try:
            new_full.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(old_file, new_full)
            return str(new_relative)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'    ❌ Ошибка копирования {old_file} -> {new_full}: {e}'))
            return ''