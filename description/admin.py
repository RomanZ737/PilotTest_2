from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import DescriptionPage


@admin.register(DescriptionPage)
class DescriptionPageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug')
    prepopulated_fields = {'slug': ('title',)}