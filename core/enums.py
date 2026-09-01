from django.db import models


# Выбор типа ВС
class ACType(models.TextChoices):
    B737 = 'B737', 'Boeing 737'
    B777 = 'B777', 'Boeing 777'
    A32X = 'A32X', 'Airbus 32X'
    A33X = 'A33X', 'Airbus 33X'
    ANY = 'MULTY', 'MULTY TYPE'


# Выбор типа Вопроса
class QType(models.TextChoices):
    SINGLE = 'SINGLE', 'Один ответ'
    MULTY = 'MULTY', 'Множественный ответ'


class Position(models.TextChoices):
    PIC = 'КВС', 'Командир ВС'
    COPILOT = 'ВП', 'Второй пилот'
    INSTRUCTOR = 'ПИ', 'Пилот-инструктор'