import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import pymysql
from django.conf import settings
from questions.models import Question, QuestionDraft, QuestionParaphrase
from core.enums import QType

print("🔍 Подключение к старой базе...")

# 1. Подключаемся к старой базе MySQL
old_db = settings.DATABASES['old_db']
conn = pymysql.connect(
    host=old_db['HOST'],
    user=old_db['USER'],
    password=old_db['PASSWORD'],
    database=old_db['NAME'],
    port=int(old_db['PORT']),
    charset='utf8mb4',
)

# 2. Получаем все записи из старой базы (ID и q_kind)
old_data = {}
with conn.cursor(pymysql.cursors.DictCursor) as cursor:
    cursor.execute("SELECT id, q_kind FROM quize737_questionset")
    for row in cursor.fetchall():
        old_data[row['id']] = row['q_kind']
conn.close()

print(f"✅ Загружено {len(old_data)} записей из старой базы")


# 3. Функция для исправления модели
def fix_model(model, model_name):
    fixed = 0
    not_found = 0
    already_correct = 0

    for q in model.objects.all():
        old_q_kind = old_data.get(q.id)

        if old_q_kind is None:
            not_found += 1
            continue

        # Преобразуем старое значение (булево) в новое
        if old_q_kind == 1:  # в старой базе 1 = несколько правильных ответов
            correct_value = QType.MULTY
        elif old_q_kind == 0:  # в старой базе 0 = один правильный ответ
            correct_value = QType.SINGLE
        else:
            continue

        if q.q_kind != correct_value:
            q.q_kind = correct_value
            q.save(update_fields=['q_kind'])
            fixed += 1
            print(f"🔄 Исправлен {model_name} ID: {q.id} (было: {q.q_kind}, стало: {correct_value})")
        else:
            already_correct += 1

    print(f"\n📊 {model_name}:")
    print(f"  - Исправлено: {fixed}")
    print(f"  - Уже правильно: {already_correct}")
    print(f"  - Не найдено в старой базе: {not_found}")


# 4. Запускаем для всех моделей
fix_model(Question, "Question")
fix_model(QuestionDraft, "QuestionDraft")
fix_model(QuestionParaphrase, "QuestionParaphrase")

print("\n✅ Готово!")