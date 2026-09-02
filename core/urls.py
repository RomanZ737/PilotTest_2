from django.urls import path
from .views import HomeListView, notification_flags_ajax

app_name = 'core'

urlpatterns = [
    path('', HomeListView.as_view(), name='home'),
    path('ajax/notifications/', notification_flags_ajax, name='ajax_notifications'),

]