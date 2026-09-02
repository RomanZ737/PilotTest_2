from django.urls import path
from .views import HomeListView, nav_bar_ajax

app_name = 'core'

urlpatterns = [
    path('', HomeListView.as_view(), name='home'),
    path('ajax/navbar/', nav_bar_ajax, name='ajax_navbar'),
]