from django.urls import path
from . import views

app_name = 'shifts'

urlpatterns = [
    path('home/', views.home, name='home'),
    path('requests/', views.shift_request_view, name='shift_request'),
    path('patterns/', views.shift_pattern_view, name='shift_pattern'),

]