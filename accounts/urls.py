from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup', views.signup, name='signup'),
    path('login', views.user_login, name='login'),
    path('logout', views.user_logout, name='logout'),
    path('manage', views.user_manage_view, name='user_manage'),
    path('delete/<int:user_id>',views.user_delete_view, name='user_delete' )
    
]
