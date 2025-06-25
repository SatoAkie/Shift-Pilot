from django.contrib import admin
from .models import ShiftRequest

@admin.register(ShiftRequest)
class ShiftRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'comment')
    list_filter = ('date', 'user')
