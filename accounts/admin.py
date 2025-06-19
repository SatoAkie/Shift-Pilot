from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Role, Team

@admin.register(Role)
class RoleAdmin (admin.ModelAdmin):
    list_display = ('role_name',)
    

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('id',)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ('email', 'name')
    search_fields = ('email', 'name')
    ordering = ('name',) 