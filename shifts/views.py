from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from datetime import date, timedelta, datetime
import calendar
from .models import ShiftRequest, ShiftPattern, PatternAssignmentSummary,User
from django.views.decorators.csrf import csrf_exempt
from collections import defaultdict


@login_required
def home(request):
    return render(
        request, 'shifts/home.html'
    )

@login_required
def shift_request_view(request):
    today = date.today() 
    month_param = request.GET.get('month')
    if month_param:
        current_date = datetime.strptime(month_param, "%Y-%m").date()
    else:
        current_date = today
        
    year = current_date.year
    month = current_date.month

    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    calendar_days = [first_day + timedelta(days=i) for i in range ((last_day - first_day).days + 1)]

    existing_requests = ShiftRequest.objects.filter(user=request.user, date__range=(first_day,last_day))
    existing_dates = set(existing_requests.values_list('date', flat=True))

    current_month = date(year, month, 1)
    prev_month = (current_month.replace(day=1) - timedelta(days=1)).replace(day=1)
    next_month = (current_month.replace(day=28) + timedelta(days=4)).replace(day=1)

    prev_month_str = prev_month.strftime("%Y-%m")
    next_month_str = next_month.strftime("%Y-%m")

    if request.method == "POST":
        selected_dates = request.POST.getlist("selected_dates")
        
        for date_str in [d.strftime('%Y-%m-%d') for d in calendar_days]:
            day = date.fromisoformat(date_str)
            comment_key = f"comment_{date_str}"
            comment = request.POST.get(comment_key,"").strip()
            is_day_off = date_str in selected_dates

            if not is_day_off and not comment:
                ShiftRequest.objects.filter(user=request.user, date=day).delete()
                continue

            ShiftRequest.objects.update_or_create(
                user=request.user, 
                date=day,
                defaults={
                    'is_day_off':is_day_off,
                    'comment':comment
                }
            )
        return redirect('shifts:shift_request')

    return render(
        request, 'shifts/shift_request.html', {
            'year': year,
            'month': month,
            'calendar_days': calendar_days,
            'existing_requests': existing_requests,
            'existing_dates': existing_dates,
            'current_month' : current_month,
            'prev_month_str' : prev_month_str,
            'next_month_str' : next_month_str
        
        }
    )

@login_required
def shift_pattern_view(request):
    if request.method == 'POST':
        total = int(request.POST.get('total', 0))
       
        for i in range(1, total + 1):
            pattern_id = request.POST.get( f'id_{i}')
            pattern_data = {
                'pattern_name': request.POST.get(f'pattern_name_{i}', f'パターン{i}'),
                'start_time': request.POST.get(f'start_time_{i}', '00:00'),
                'end_time': request.POST.get(f'end_time_{i}', '00:00'),
                'max_people': request.POST.get(f'max_people_{i}',1)
            }
        
            if pattern_id:
                pattern = get_object_or_404(ShiftPattern, pk=pattern_id)
                for key,value in pattern_data.items():
                    setattr(pattern, key, value)
                pattern.save()
            else:
                ShiftPattern.objects.create(**pattern_data)
        return redirect('shifts:shift_pattern')       

    if ShiftPattern.objects.count() == 0:
        for char in ['A', 'B', 'C', 'D']:
            ShiftPattern.objects.create(
                pattern_name=char,
                start_time='00:00',
                end_time='00:00',
                max_people=1
            )
    patterns = ShiftPattern.objects.all()    
    return render(request,'shifts/shift_pattern.html',{
        'patterns': patterns,
    })

@login_required
def pattern_assignment_summary_view(request):
    today = date.today()
    month_param = request.GET.get('month')
    if month_param:
        current_date = datetime.strptime(month_param, "%Y-%m").date()
    else:
        current_date = today

    year = current_date.year
    month = current_date.month
    summaries = PatternAssignmentSummary.objects.filter(summary_year=year, summary_month=month)
    users = User.objects.all()
    patterns = ShiftPattern.objects.all()

    summary_dict = defaultdict(lambda: defaultdict(int))
    for s in summaries:
        summary_dict[s.user_id][s.pattern_id] = s.assignment_count

    max_counts = defaultdict(dict)
    for user_id, pattern_counts in summary_dict.items():
        if pattern_counts:
            max_value = max(pattern_counts.values())
            for pattern_id, count in pattern_counts.items():
                if count == max_value:
                    max_counts[user_id][pattern_id] = True

    total_work_hours = defaultdict(float)
    for summary in summaries:
        if summary.pattern and summary.user:
            start = datetime.combine(date.today(), summary.pattern.start_time)
            end = datetime.combine(date.today(), summary.pattern.end_time)
            hours = (end - start).seconds / 3600 
            total_work_hours[summary.user_id] += hours * summary.assignment_count   

    if month == 12:
        last_day = date(year, 12, 31)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    first_day =  date(year, month, 1)  

    dayoff_counts = defaultdict(int)
    requests = ShiftRequest.objects.filter(date__range =(first_day, last_day), is_day_off=True)
    for req in requests:
        dayoff_counts[req.user_id] += 1         

    current_month = date(year, month, 1)
    prev_month = (current_month.replace(day=1) - timedelta(days=1)).replace(day=1)
    next_month = (current_month.replace(day=28) + timedelta(days=4)).replace(day=1)

    prev_month_str = prev_month.strftime("%Y-%m")
    next_month_str = next_month.strftime("%Y-%m")
                           
    return render(request,'shifts/pattern_assignment_summary.html',{
        'year': year,
        'month': month,
        'current_month': current_month, 
        'users': users,
        'patterns': patterns,
        'summary_dict': summary_dict,
        'max_counts': max_counts,
        'total_work_hours': total_work_hours,
        'dayoff_counts': dayoff_counts,
        'prev_month_str': prev_month_str,
        'next_month_str': next_month_str,
        
    })