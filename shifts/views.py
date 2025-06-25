from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from datetime import date, timedelta
import calendar
from .models import  ShiftRequest

@login_required
def home(request):
    return render(
        request, 'shifts/home.html'
    )

@login_required
def shift_request_view(request):
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month',today.month))

    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    calendar_days = [first_day + timedelta(days=i) for i in range ((last_day - first_day).days + 1)]

    existing_requests = ShiftRequest.objects.filter(user=request.user, date__range=(first_day,last_day))

    if request.method == "POST":
        selected_dates = request.POST.getlist("selected_dates")
        ShiftRequest.objects.filter(user=request.user, date__range=(first_day, last_day)).delete()
        for date_str in selected_dates:
            ShiftRequest.objects.create(user=request.user, date=date.fromisoformat(date_str))
        return redirect('shift_request_view')

    return render(
        request, 'shifts/shift_request.html',context= {
            'year': year,
            'month': month,
            'calendar_days': calendar_days,
            'existing_requests': existing_requests,
        }
    )