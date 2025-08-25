from django.urls import path
from . import views

app_name = 'shifts'

urlpatterns = [
    path('home/', views.home, name='home'),
    path('requests/', views.shift_request_view, name='shift_request'),
    path('patterns/', views.shift_pattern_view, name='shift_pattern'),
    path('patterns/delete/<int:pattern_id>/', views.delete_pattern_view, name='delete_pattern'),
    path('pattern_assignment_summaries/', views.pattern_assignment_summary_view, name='pattern_assignment_summaries'),
    path('create/', views.shift_create_view, name='shift_create'),
    path('assign/', views.auto_assign_shifts, name='shifts'),
    path('update-user-shift/', views.update_user_shift, name='update_user_shift'), 
    path("toggle_all_rest/", views.toggle_all_rest, name="toggle_all_rest"),
]