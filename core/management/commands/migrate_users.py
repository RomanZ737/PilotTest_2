import pymysql
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Group
from django.conf import settings
from users.models import CustomUser, GroupsDescription
from django.utils import timezone
import datetime

FIXED_GROUPS = [
    'KRS', 'ВП B737', 'КВС B737', 'ПИ B737', 'Редактор',
    'ВП B777', 'КВС B777', 'ПИ B777',
    'ВП A32X', 'КВС A32X', 'ПИ A32X',
    'ВП A33X', 'КВС A33X', 'ПИ A33X',
]


class Command(BaseCommand):
    help = 'Перенос пользователей и групп из старой БД через pymysql'

    def add_arguments(self, parser):
        parser.add_argument(
            '--old-db',
            type=str,
            default='old_db',
            help='Имя соединения с БД в settings.py (по умолчанию "old_db")'
        )

    def handle(self, *args, **options):
        self.old_db = options['old_db']

        db_settings = settings.DATABASES[self.old_db]

        try:
            conn = pymysql.connect(
                host=db_settings['HOST'],
                user=db_settings['USER'],
                password=db_settings['PASSWORD'],
                database=db_settings['NAME'],
                port=int(db_settings['PORT']),
                charset='utf8mb4',
            )
        except Exception as e:
            raise CommandError(f'Не удалось подключиться к старой БД: {e}')

        cursor = conn.cursor(pymysql.cursors.DictCursor)

        try:
            # ============================================
            # 1. Перенос групп
            # ============================================
            self.stdout.write('Перенос групп...')

            cursor.execute("SELECT id, name FROM auth_group")
            old_groups = cursor.fetchall()

            group_map = {}

            for row in old_groups:
                old_id = row['id']
                name = row['name']

                group, created = Group.objects.get_or_create(name=name)
                group_map[old_id] = group

                GroupsDescription.objects.get_or_create(
                    group=group,
                    defaults={
                        'description': f'Группа {name}',
                        'is_fixed': name in FIXED_GROUPS,
                    }
                )

                if created:
                    self.stdout.write(f'  + Группа: {name}')
                else:
                    self.stdout.write(f'  = Группа уже существует: {name}')

            # ============================================
            # 2. Перенос пользователей
            # ============================================
            self.stdout.write('Перенос пользователей...')

            cursor.execute("""
                SELECT
                    u.id, u.username, u.email, u.password,
                    u.first_name, u.last_name,
                    u.is_active, u.is_staff, u.is_superuser,
                    u.date_joined, u.last_login,
                    p.family_name, p.first_name AS p_first_name,
                    p.middle_name, p.position, p.ac_type
                FROM auth_user u
                LEFT JOIN users_profile p ON u.id = p.user_id
            """)
            old_users = cursor.fetchall()

            user_map = {}
            skipped = 0

            for row in old_users:
                old_id = row['id']
                username = row['username']
                email = row['email']
                password = row['password']

                # Если email пустой — генерируем
                if not email:
                    email = f'{username}@pilot.local'

                # Проверяем уникальность email
                if CustomUser.objects.filter(email=email).exists():
                    self.stdout.write(f'  ! Пропущен {username} — email {email} уже существует')
                    skipped += 1
                    continue

                if CustomUser.objects.filter(username=username).exists():
                    self.stdout.write(f'  ! Пропущен {username} — username уже существует')
                    skipped += 1
                    continue

                # Приводим даты к timezone-aware, если они naive
                date_joined = row['date_joined']
                if date_joined and timezone.is_naive(date_joined):
                    date_joined = timezone.make_aware(date_joined)

                last_login = row['last_login']
                if last_login and timezone.is_naive(last_login):
                    last_login = timezone.make_aware(last_login)

                user = CustomUser.objects.create(
                    username=username,
                    email=email,
                    password=password,  # Хеш копируется как есть
                    first_name=row['p_first_name'] or row['first_name'] or '',
                    last_name=row['family_name'] or row['last_name'] or '',
                    middle_name=row['middle_name'] or '',
                    position=row['position'] or '',
                    ac_type=row['ac_type'] or '',
                    is_active=row['is_active'],
                    is_staff=row['is_staff'],
                    is_superuser=row['is_superuser'],
                    date_joined=row['date_joined'],
                    last_login=row['last_login'],
                    is_email_verified=True,
                )

                user_map[old_id] = user
                self.stdout.write(f'  + {email}')

            # ============================================
            # 3. Связываем пользователей с группами
            # ============================================
            self.stdout.write('Связывание пользователей с группами...')

            cursor.execute("SELECT user_id, group_id FROM auth_user_groups")
            memberships = cursor.fetchall()

            for row in memberships:
                user = user_map.get(row['user_id'])
                group = group_map.get(row['group_id'])
                if user and group:
                    user.groups.add(group)

            # ============================================
            # Итоги
            # ============================================
            self.stdout.write(self.style.SUCCESS(
                f'\nГотово! Перенесено:'
                f'\n  Групп: {len(group_map)}'
                f'\n  Пользователей: {len(user_map)}'
                f'\n  Пропущено: {skipped}'
            ))

        finally:
            cursor.close()
            conn.close()