from django.contrib import admin
from .models import CustomUser, GroupsDescription
from django.contrib.auth.models import Group
from django.contrib.auth.admin import GroupAdmin


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone_number', 'username', 'is_staff', 'is_superuser')
    list_filter = ('is_staff', 'is_superuser')
    search_fields = ('email', 'fist_name', 'last_name')


class GroupsDescriptionInline(admin.StackedInline):
    model = GroupsDescription
    can_delete = False
    verbose_name = 'Описание группы'
    verbose_name_plural = 'Описание групп'


# Расширяем стандартную админку групп
admin.site.unregister(Group)


@admin.register(Group)
class CustomGroupAdmin(GroupAdmin):
    inlines = [GroupsDescriptionInline]
    list_display = ('name', 'get_description', 'get_is_fixed', 'get_pilot_count')

    @admin.display(description='Описание')
    def get_description(self, obj):
        desc = GroupsDescription.objects.filter(group=obj).first()
        return desc.description if desc else '—'

    @admin.display(description='Фиксированная', boolean=True)
    def get_is_fixed(self, obj):
        desc = GroupsDescription.objects.filter(group=obj).first()
        return desc.is_fixed if desc else False

    @admin.display(description='Пилотов')
    def get_pilot_count(self, obj):
        return obj.user_set.count()
