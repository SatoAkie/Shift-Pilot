from django.contrib import admin
from .models import Shift, UserShift, ShiftRequest, ShiftPattern, PatternAssignmentSummary

@admin.register(ShiftRequest)
class ShiftRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'comment')
    list_filter = ('date', 'user')

admin.site.register(Shift)
admin.site.register(ShiftPattern)
admin.site.register(UserShift) 
admin.site.register(PatternAssignmentSummary)