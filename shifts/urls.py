from django.urls import path
from . import views

app_name = 'shifts'

urlpatterns = [
    path('home/', views.home, name='home'),
    path('requests/', views.shift_request_view, name='shift_request'),
    path('patterns/', views.shift_pattern_view, name='shift_pattern'),
    path('pattern_assignment_summaries/', views.pattern_assignment_summary_view, name='pattern_assignment_summaries'),

]