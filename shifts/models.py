from django.db import models
from django.conf import settings

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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.pattern_name}（{self.start_time}〜{self.end_time}）"

