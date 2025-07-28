from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
from accounts.models import Team

User = get_user_model()

class ShiftRequest(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField()
    is_day_off = models.BooleanField(default=False) 
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user' , 'date')

    def __str__(self):
        return f"{self.user} requests off on {self.date}"
    

class ShiftPattern(models.Model):
    pattern_name = models.CharField(max_length=128)
    start_time = models.TimeField()
    end_time = models.TimeField()
    max_people = models.IntegerField()
    is_rest = models.BooleanField(default=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.pattern_name}（{self.start_time}〜{self.end_time}）"

class Shift(models.Model):
    pattern = models.ForeignKey('ShiftPattern', on_delete=models.SET_NULL, null=True)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('date', 'team', 'pattern')

    def __str__(self):
        return f"{self.date} - {self.team} - {self.pattern}"

class UserShift(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    shift = models.ForeignKey('Shift', null=True, blank=True, on_delete=models.SET_NULL)
    date = models.DateField()
    is_manual = models.BooleanField(default=False)
    is_error = models.BooleanField(default=False)

    class Meta:
       constraints = [
            models.UniqueConstraint(fields=['user', 'date'], name='unique_user_date')
        ]
    def __str__(self):
        if self.shift:
            return f"{self.user.name} - {self.shift.date} - {self.shift.pattern.pattern_name}"
        else:
            return f"{self.user.name} - 休（{self.date}）"

    
class PatternAssignmentSummary(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    pattern = models.ForeignKey(ShiftPattern, on_delete=models.SET_NULL, null=True)

    summary_year = models.IntegerField()
    summary_month = models.IntegerField()
    assignment_count = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.pattern} ({self.summary_year}/{self.summary_month}): {self.assignment_count}回"
