from django.urls import path
from . import views

app_name = 'description'

urlpatterns = [
    path('', views.DescriptionIndexView.as_view(), name='index'),
    path('<slug:slug>/', views.DescriptionDetailView.as_view(), name='detail'),
    path('<slug:slug>/edit/', views.DescriptionUpdateView.as_view(), name='edit'),
]