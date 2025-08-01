from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from datetime import date, timedelta, datetime
import calendar, json
from .models import ShiftRequest, ShiftPattern, Shift, UserShift, PatternAssignmentSummary,User
from django.views.decorators.csrf import csrf_exempt
from collections import defaultdict
from calendar import Calendar,monthrange
from .utils import assign_shifts
from django.http import JsonResponse
from django.urls import reverse
from django.contrib import messages

@login_required
def home(request):
    today = date.today()
    month_param = request.GET.get("month")
    current_date = datetime.strptime(month_param, "%Y-%m").date() if month_param else today

    year = current_date.year
    month = current_date.month
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    calendar_days = [first_day + timedelta(days=i) for i in range((last_day - first_day).days + 1)]

    users = User.objects.filter(team=request.user.team)
    user_shifts = UserShift.objects.filter(
        date__range=(first_day, last_day), user__in=users
    ).select_related('shift__pattern', 'shift')

    shift_dict = {user.id: {} for user in users}
    for shift in user_shifts:
        if shift.shift is None:
            continue  

        day = shift.shift.date.day
        if day in shift_dict[shift.user.id]:
            continue
        shift_dict[shift.user.id][day] = shift.shift.pattern.id if shift.shift.pattern else ""



    patterns = ShiftPattern.objects.filter(team=request.user.team)

    context = {
        "calendar_days": calendar_days,
        "users": users,
        "shift_dict": shift_dict,
        "patterns": patterns,
        "current_month": current_date,
        "prev_month_str": (first_day - timedelta(days=1)).strftime("%Y-%m"),
        "next_month_str": (last_day + timedelta(days=1)).strftime("%Y-%m"),
    }

    return render(request, "shifts/home.html", context)


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

    cal = Calendar(firstweekday=0) 
    month_weeks = cal.monthdatescalendar(year, month)  
    calendar_days = [day for week in month_weeks for day in week] 

    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    existing_requests = ShiftRequest.objects.filter(user=request.user, date__range=(first_day,last_day))
    day_off_dates = set(existing_requests.filter(is_day_off=True).values_list('date', flat=True))
    comment_dates = set(existing_requests.exclude(comment="").exclude(comment__isnull=True).values_list('date', flat=True))
    existing_dates = set(existing_requests.values_list('date', flat=True))

    current_month = date(year, month, 1)
    prev_month = (current_month.replace(day=1) - timedelta(days=1)).replace(day=1)
    next_month = (current_month.replace(day=28) + timedelta(days=4)).replace(day=1)

    prev_month_str = prev_month.strftime("%Y-%m")
    next_month_str = next_month.strftime("%Y-%m")

    if request.method == "POST":
        selected_dates = request.POST.getlist("selected_dates")
        if not selected_dates:
            messages.error(request, "日付を選択してください")
            return redirect('shifts:shift_request')
        
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

        messages.success(request, "申請が完了しました。")
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
            'next_month_str' : next_month_str,
            'day_off_dates': day_off_dates,
            'comment_dates': comment_dates,
        
        }
    )

@login_required
def shift_pattern_view(request):
    if request.method == 'POST':
        total = int(request.POST.get('total', 0))
        pattern_list = []
        error_message = None

        for i in range(1, total + 1):
            pattern_id = request.POST.get(f'id_{i}', '').strip()
            name = request.POST.get(f'pattern_name_{i}', '').strip()
            start = request.POST.get(f'start_time_{i}', '').strip()
            end = request.POST.get(f'end_time_{i}', '').strip()
            max_people_raw = request.POST.get(f'max_people_{i}', '').strip()
        
            pattern_data = {
                'id': pattern_id,
                'pattern_name': name,
                'start_time': start,
                'end_time': end,
                'max_people': max_people_raw,
            }

            if not (name and start and end and max_people_raw):
                error_message = 'すべての項目を入力してください'
            else:
                try:
                    pattern_data['max_people'] = int(max_people_raw)
                except ValueError:
                        error_message = '人数は整数で入力してください'
            
            pattern_list.append(pattern_data)

        if error_message:
            return render(request, 'shifts/shift_pattern.html', {
                                'patterns': pattern_list,
                                'error_message': error_message
                            })

        for data in pattern_list:
            if data['id']:
                pattern = get_object_or_404(ShiftPattern, pk=data['id'], team=request.user.team)
                pattern.pattern_name = data['pattern_name']
                pattern.start_time = data['start_time']
                pattern.end_time = data['end_time']
                pattern.max_people = data['max_people']
                pattern.save()
            else:
                ShiftPattern.objects.create(
                    pattern_name=data['pattern_name'],
                    start_time=data['start_time'],
                    end_time=data['end_time'],
                    max_people=data['max_people'],
                    team=request.user.team
                )
        messages.success(request, "シフトパターンを登録しました")
        return redirect('shifts:shift_pattern')
    
    patterns = ShiftPattern.objects.filter(team=request.user.team)   
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
    team = request.user.team
    
    summaries = PatternAssignmentSummary.objects.filter(
        summary_year=year, 
        summary_month=month,
        user__team =team
    )

    if not summaries.exists():
        messages.error(request, "この月のシフトが存在しません")

    users = User.objects.filter(team=team)
    patterns = ShiftPattern.objects.filter(team=request.user.team)

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

    rest_counts = defaultdict(int)
    for user in users:
        rest_count = UserShift.objects.filter(
            user=user,
            date__range=(first_day, last_day),
            shift__isnull=True,
            is_error=False
        ).count()
        rest_counts[user.id] = rest_count



    dayoff_counts = defaultdict(int)
    requests = ShiftRequest.objects.filter(
        date__range =(first_day, last_day), 
        is_day_off=True,
        user__team=team
        )
    for req in requests:
        dayoff_counts[req.user_id] += 1   

    combined_rest_counts = defaultdict(int)
    for user in users:
        requested = dayoff_counts.get(user.id, 0)
        actual_rest = rest_counts.get(user.id, 0)
        combined_rest_counts[user.id] = requested + actual_rest      

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
        'combined_rest_counts': combined_rest_counts, 
        'prev_month_str': prev_month_str,
        'next_month_str': next_month_str,
        
    })

@login_required
def shift_create_view(request):
    month_param = request.GET.get('month')
    if month_param:
        try:
            current_date = datetime.strptime(month_param, "%Y-%m").date()
        except ValueError:
            current_date = date.today()
    else:
        current_date = date.today()

    year = current_date.year
    month = current_date.month
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])
    calendar_days = [first_day + timedelta(days=i) for i in range((last_day - first_day).days + 1)]

    prev_month = (first_day.replace(day=1) - timedelta(days=1)).replace(day=1)
    next_month = (first_day.replace(day=28) + timedelta(days=4)).replace(day=1)
    prev_month_str = prev_month.strftime('%Y-%m')
    next_month_str = next_month.strftime('%Y-%m')

    team = request.user.team
    users = team.user_set.all()
    
    user_shifts = UserShift.objects.filter(
        date__range=(first_day, last_day),
        user__in=users
    ).select_related('user', 'shift__pattern')

    shift_dict = defaultdict(dict)
    error_dict = defaultdict(dict)
    for us in user_shifts:
        shift_dict[us.user_id][us.date] = us

        if us.shift is None and us.is_error:
            error_dict[us.user_id][us.date.day] = True
        else:
            error_dict[us.user_id][us.date.day] = False

    comment_dict = {user.id: {} for user in users}
    comment_requests = ShiftRequest.objects.filter(
        date__range=(first_day, last_day),
        comment__isnull=False
    ).exclude(comment='').filter(user__in=users)

    for req in comment_requests:
        comment_dict[req.user.id][req.date.day] = req.comment
    
    return render(request, 'shifts/shift_create.html',{
        'users': users,
        'current_month': current_date,
        'calendar_days': calendar_days,
        'shift_dict': shift_dict,
        'error_dict': error_dict, 
        'comment_dict': comment_dict,
        'patterns': ShiftPattern.objects.filter(team=request.user.team),
        'prev_month_str': prev_month_str,
        'next_month_str': next_month_str,
    })

@login_required
def auto_assign_shifts(request):
    if request.method == 'POST':
        month_param = request.GET.get("month")
        if month_param:
            current_date = datetime.strptime(month_param, "%Y-%m").date()
        else:
            current_date = date.today()
        year = current_date.year
        month = current_date.month

        team = request.user.team

        if not ShiftPattern.objects.exists():
            messages.error(request, '勤務パターンが登録されていないため、シフトを自動作成できません。')
            return redirect(f'{reverse("shifts:shift_create")}?month={month_param or date.today().strftime("%Y-%m")}')

        patterns = ShiftPattern.objects.all()
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])
        calendar_days = [first_day + timedelta(days=i) for i in range((last_day - first_day).days + 1)]

        existing_shift_keys = set(
            Shift.objects.filter(date__range=(first_day, last_day), team=team)
            .values_list('date', 'pattern_id')
        )

        new_shifts = []
        for day in calendar_days:
            for pattern in patterns:
                if (day, pattern.id) not in existing_shift_keys:
                    new_shifts.append(Shift(date=day, pattern=pattern, team=team))

        Shift.objects.bulk_create(new_shifts)

        shifts = Shift.objects.filter(date__range=(first_day, last_day), team=team)
        users = team.user_set.all()

        UserShift.objects.filter(
            date__range=(first_day, last_day),
            user__in=users,
            is_manual=False
        ).delete()
        
        shift_requests = {}
        for req in ShiftRequest.objects.filter(date__range=(first_day, last_day)):
            shift_requests.setdefault(req.user_id, set()).add(req.date)

        valid_shifts = [s for s in shifts if s.pattern is not None]

        assigned, errors = assign_shifts(users, valid_shifts, shift_requests)
        for msg in errors:
            messages.error(request, msg)

        existing_user_date_pairs = set(
            UserShift.objects.filter(
                date__range=(first_day, last_day),
                user__in=users
            ).values_list('user_id', 'date')
        )

        new_user_shifts = [
            us for us in assigned
            if (us.user.id, us.date) not in existing_user_date_pairs
        ]

        UserShift.objects.bulk_create(new_user_shifts)

        PatternAssignmentSummary.objects.filter(
            user__in=users,
            summary_year=year,
            summary_month=month
        ).delete()

        summary_counter = defaultdict(lambda: defaultdict(int))

        for us in UserShift.objects.filter(date__range=(first_day, last_day), user__in=users):
            if us.shift and us.shift.pattern:
                summary_counter[us.user][us.shift.pattern] += 1
            elif us.shift is None and not us.is_error:  
                summary_counter[us.user][None] += 1    


        new_summaries = []
        for user, pattern_counts in summary_counter.items():
            for pattern, count in pattern_counts.items():
                new_summaries.append(PatternAssignmentSummary(
                    user=user,
                    pattern=pattern,
                    assignment_count=count,
                    summary_year=year,
                    summary_month=month
                ))

        PatternAssignmentSummary.objects.bulk_create(new_summaries)

        rest_counts = defaultdict(int)
        for us in UserShift.objects.filter(date__range=(first_day, last_day), user__in=users):
            if us.shift is None and not us.is_error:
                rest_counts[us.user.id] += 1

        request.session['rest_counts'] = dict(rest_counts)

        return redirect(f'{reverse("shifts:shift_create")}?month={month_param or current_date.strftime("%Y-%m")}')
                                                                  

@csrf_exempt
def update_user_shift(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            date_str = data.get('date')
            pattern_id = data.get('pattern_id')  

            if not user_id or not date_str:
                return JsonResponse({'success': False, 'message': '必要な値が不足しています'}, status=400)

            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            user = get_object_or_404(User, pk=user_id)

            pattern = None
            if pattern_id not in ("", None):
                pattern = get_object_or_404(ShiftPattern, pk=pattern_id)

            shift = None
            if pattern:
                shift, _ = Shift.objects.get_or_create(
                    date=date_obj,
                    team=user.team,
                    pattern=pattern
                )

            user_shift, created = UserShift.objects.get_or_create(
                user=user,
                date=date_obj,
                defaults={
                    'shift': shift,
                    'is_manual': True,
                    'is_error': False if shift else True
                }
            )

            if not created:
                user_shift.shift = shift
                user_shift.is_manual = True
                user_shift.is_error = False if shift else True
                user_shift.save()

            return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': False, 'error': 'POSTのみ対応'}, status=405)
