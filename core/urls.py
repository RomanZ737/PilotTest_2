from django.urls import path
from .views import HomeListView


app_name = 'core'

urlpatterns = [
    path('', HomeListView.as_view(template_name='core/home.html'), name='home'),
]