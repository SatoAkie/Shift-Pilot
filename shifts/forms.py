from django import forms
from .models import ShiftPattern

class ShiftPatternForm(forms.ModelForm):
    class Meta:
       model = ShiftPattern
       fields = ('pattern_name', 'start_time', 'end_time', 'max_people')