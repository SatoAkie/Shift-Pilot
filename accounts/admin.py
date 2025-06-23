from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Role, Team
from django.utils.translation import gettext_lazy as _

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('role_name',)

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('id',)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User

    list_display = ('email', 'name', 'role', 'team', 'is_staff', 'is_active')
    search_fields = ('email', 'name')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('名前', {'fields': ('name',)}),
        ('所属', {'fields': ('team', 'role')}),
        ('パーミッション', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('ログイン情報', {'fields': ('last_login',)}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'password1', 'password2', 'team', 'role', 'is_staff', 'is_active'),
        }),
    )
