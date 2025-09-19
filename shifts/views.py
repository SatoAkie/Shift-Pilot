from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from datetime import date, timedelta, datetime
import calendar, json
from django.db.models import Count, Q  
from .models import ShiftRequest, ShiftPattern, Shift, UserShift, PatternAssignmentSummary,User,AllUserRestDay
from django.views.decorators.csrf import csrf_exempt
from collections import defaultdict
from calendar import Calendar,monthrange
from .utils import assign_shifts
from django.http import JsonResponse
from django.urls import reverse
from django.contrib import messages
from django.utils.dateparse import parse_date

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
    error_dict = defaultdict(set)

    for shift in user_shifts: 
        day = shift.date.day

        if shift.shift is None:
            if shift.is_error:
                error_dict[shift.user.id].add(day)
            continue  

        if day in shift_dict[shift.user.id]:
            continue
        if shift.shift.pattern:
            shift_dict[shift.user.id][day] = shift.shift.pattern.id
        else:
            shift_dict[shift.user.id][day] = "deleted"



    patterns = ShiftPattern.objects.filter(team=request.user.team)

    context = {
        "calendar_days": calendar_days,
        "users": users,
        "shift_dict": shift_dict,
        "error_dict": error_dict,
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

    comment_dict = {req.date: req.comment for req in existing_requests if req.comment}
    
    current_month = date(year, month, 1)
    prev_month = (current_month.replace(day=1) - timedelta(days=1)).replace(day=1)
    next_month = (current_month.replace(day=28) + timedelta(days=4)).replace(day=1)

    prev_month_str = prev_month.strftime("%Y-%m")
    next_month_str = next_month.strftime("%Y-%m")

    if request.method == "POST":
        selected_dates = request.POST.getlist("selected_dates")
        if not selected_dates:
            has_comment = any(
                request.POST.get(f"comment_{d.strftime('%Y-%m-%d')}", "").strip()
                for d in calendar_days
            )
            if not has_comment:
                messages.error(request, "日付を選択するか、コメントを入力してください。")
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
            'comment_dict': comment_dict, 
        
        }
    )

@login_required
def shift_pattern_view(request):
    if request.method == 'POST':
        total = int(request.POST.get('total', 0))
        pattern_list = []
        error_dict = {}

        for i in range(1, total + 1):
            pattern_id = request.POST.get(f'id_{i}', '').strip()
            name = request.POST.get(f'pattern_name_{i}', '').strip()
            start = request.POST.get(f'start_time_{i}', '').strip()
            end = request.POST.get(f'end_time_{i}', '').strip()
            max_people_raw = request.POST.get(f'max_people_{i}', '').strip()
        
            if not (name and start and end and max_people_raw):
                continue

            start_time = datetime.strptime(start, "%H:%M").time()
            end_time = datetime.strptime(end, "%H:%M").time()
            max_people = int(max_people_raw)

            
            total_minutes = (datetime.combine(date.today(),end_time) - datetime.combine(date.today(),start_time)).seconds //60
            work_hours = (total_minutes - 60) / 60

            if work_hours > 12:
                error_dict[i] = "労働時間は12時間を超えないようにしてください"

            pattern_data = {
                'id': pattern_id,
                'pattern_name': name,
                'start_time': start_time,
                'end_time': end_time,
                'max_people': max_people,
            }
            pattern_list.append(pattern_data)

        if error_dict:
            patterns = ShiftPattern.objects.filter(team=request.user.team)
            return render(request, 'shifts/shift_pattern.html', {
                'patterns': pattern_list,
                'error_dict': error_dict,
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
def delete_pattern_view(request,pattern_id):
    pattern = get_object_or_404(ShiftPattern, id=pattern_id, team=request.user.team)

    pattern.delete()
    messages.success(request, f'シフトパターン「{pattern.pattern_name}」を削除しました')
    return redirect('shifts:shift_pattern')


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

    pattern_user_counts = defaultdict(lambda: defaultdict(int))  
    for user_id, pattern_counts in summary_dict.items():
        for pattern_id, count in pattern_counts.items():
            pattern_user_counts[pattern_id][user_id] = count

    max_counts = defaultdict(dict) 
    for pattern_id, user_counts in pattern_user_counts.items():
        if not user_counts:
            continue
        max_value = max(user_counts.values())
        for user_id, count in user_counts.items():
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
        combined_rest_counts[user.id] = rest_counts.get(user.id, 0)      

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
        elif us.shift and us.shift.pattern is None:
            error_dict[us.user_id][us.date.day] = True
            us.is_error = True
            us.shift = None 
            shift_dict[us.user_id][us.date] = us
        else:
            error_dict[us.user_id][us.date.day] = False

    comment_dict = {user.id: {} for user in users}
    comment_requests = ShiftRequest.objects.filter(
        date__range=(first_day, last_day),
        comment__isnull=False
    ).exclude(comment='').filter(user__in=users)

    for req in comment_requests:
        comment_dict[req.user.id][req.date.day] = req.comment
    
    shifts = UserShift.objects.filter(shift__team=request.user.team,date__range=(first_day, last_day))

    error_flag = False
    for us in shifts:
        if us.shift and us.shift.pattern is None:  
            error_flag = True

    if error_flag:
        messages.error(request, "削除されたシフトパターンが含まれています。再作成してください。")


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

        if not ShiftPattern.objects.filter(team=team).exists():
            messages.error(request, '勤務パターンが登録されていないため、シフトを自動作成できません。')
            return redirect(f'{reverse("shifts:shift_create")}?month={month_param or date.today().strftime("%Y-%m")}')

        patterns = ShiftPattern.objects.filter(team=team)
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
        for req in ShiftRequest.objects.filter(
            user__team=team,
            date__range=(first_day, last_day),
            is_day_off=True
        ):
            shift_requests.setdefault(req.user_id, set()).add(req.date)

        valid_shifts = [s for s in shifts if s.pattern is not None]

        assigned, errors = assign_shifts(users, valid_shifts, shift_requests)
        messages.success(request, "シフトを作成しました")
        if errors:
            messages.error(
                request,
                "勤務が一部割り当てられませんでした。赤枠で表示された部分を手動で入力してください"
            )

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

        # POSTされた全休日リスト（"YYYY-MM-DD" 形式の文字列）を取得
        rest_days = request.POST.getlist('all_user_rest_days[]')

        # 既存の指定を削除（この月・チーム分）
        AllUserRestDay.objects.filter(
            date__range=(first_day, last_day),
            team=team
        ).delete()

        # 新しい全休日を保存
        for rest_day_str in rest_days:
            try:
                rest_date = datetime.strptime(rest_day_str, "%Y-%m-%d").date()
                AllUserRestDay.objects.create(date=rest_date, team=team)
            except ValueError:
                continue  # 無効な日付文字列はスキップ


        UserShift.objects.bulk_create(new_user_shifts)

        all_user_rest_days = set(
            AllUserRestDay.objects.filter(
                date__range=(first_day, last_day),
                team=team
            ).values_list('date', flat=True)
        )

        total_users = users.count()
        if total_users == 0:
            error_dates = []
        else:
            day_stats = (
                UserShift.objects
                .filter(date__range=(first_day, last_day), user__in=users)
                .values('date')
                .annotate(
                    total=Count('id'),
                    rest_ok=Count('id', filter=Q(shift__isnull=True, is_error=False)),
                    any_work=Count('id', filter=Q(shift__isnull=False)),
                )
            )

            error_dates = [
                row['date']
                for row in day_stats
                if row['total'] == total_users
                and row['rest_ok'] == total_users
                and row['date'] not in all_user_rest_days
            ]

        if error_dates:
            UserShift.objects.filter(date__in=error_dates, user__in=users).update(is_error=True)
            messages.error(
                request,
                "一部の日が全員休みになっています。赤枠で表示された部分を手動で入力してください。"
            )


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
            is_error = False

            if pattern_id in ("", None):  
                pattern = None
                is_error = False
            elif pattern_id == "__ERROR__":  
                pattern = None
                is_error = True
            else:  
                pattern = get_object_or_404(ShiftPattern, pk=pattern_id)
                is_error = False

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
                    'is_error': is_error
                }
            )

            if not created:
                user_shift.shift = shift
                user_shift.is_manual = True
                user_shift.is_error = is_error
                user_shift.save()

            team_users = User.objects.filter(team=user.team)
            total_users = team_users.count()
          
            qs = UserShift.objects.filter(date=date_obj, user__team=user.team)
            total = qs.count()
            any_work = qs.filter(shift__isnull=False).exists()
            rest_all = qs.filter(shift__isnull=True).count() 

            is_intentional_all_rest = AllUserRestDay.objects.filter(
                date=date_obj, team=user.team
            ).exists()

            if any_work or is_intentional_all_rest:
   
                qs.filter(is_error=True).update(is_error=False)
            else:
                if total_users > 0 and total == total_users and rest_all == total_users:
                    qs.update(is_error=True)
                else:
                    qs.filter(is_error=True).update(is_error=False)

            return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': False, 'error': 'POSTのみ対応'}, status=405)

@require_POST
def toggle_all_rest(request):
    try:
        payload = json.loads(request.body)
        date_str = payload.get("date")
        checked = bool(payload.get("checked"))
        team = request.user.team

        d = parse_date(date_str)
        if not d:
            return JsonResponse({"ok": False, "error": "invalid date"}, status=400)

        qs = UserShift.objects.filter(date=d, user__team=team)

        if checked:
            # 意図的に全休にする → 記録 & 全員休（エラー解除）
            AllUserRestDay.objects.get_or_create(date=d, team=team)
            qs.update(shift=None, is_error=False)
        else:
            # 意図的全休の解除
            AllUserRestDay.objects.filter(date=d, team=team).delete()

            # その日の状態を見て is_error を再判定
            total_users = User.objects.filter(team=team).count()
            total = qs.count()
            any_work = qs.filter(shift__isnull=False).exists()

            if total_users > 0 and total == total_users and not any_work:
                # 全員休み（意図せず）→ エラー付与
                qs.update(is_error=True)
            else:
                # それ以外 → エラー解除
                qs.update(is_error=False)

        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)
