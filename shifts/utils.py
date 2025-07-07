import random
from collections import defaultdict
from datetime import datetime, date, timedelta
from .models import UserShift, ShiftPattern, Shift

def calculate_hours(start_time, end_time):
    total_minutes = (datetime.combine(date.today(), end_time) - datetime.combine(date.today(), start_time)).seconds // 60
    break_minutes = 60
    work_minutes = max(0, total_minutes - break_minutes)
    return work_minutes / 60

def assign_shifts(users, shifts, shift_requests):
    user_shift_count = defaultdict(int)
    user_assigned_dates = defaultdict(set)
    assigned_count_per_pattern = defaultdict(lambda: defaultdict(int))
    assigned_pairs = []
    weekly_hours = defaultdict(lambda: defaultdict(float)) 
    user_shift_history = defaultdict(dict)
    shift_map = defaultdict(list)
    shift_dict = {}
    user_pattern_count = defaultdict(lambda: defaultdict(int))

    errors = []

    for shift in shifts:
        shift_map[shift.date].append(shift)
        if shift.pattern:
            shift_dict[(shift.date, shift.pattern.id)] = shift

    try:
        rest_pattern = ShiftPattern.objects.get(pattern_name='○')
    except ShiftPattern.DoesNotExist:
        rest_pattern = None

    if not rest_pattern:
        return assigned_pairs, ["○（休み）パターンが登録されていません"]

    
    for user in users:
        for date in shift_requests.get(user.id, set()):
            if assigned_count_per_pattern[date][rest_pattern.id] >= rest_pattern.max_people:
                errors.append(f"{date.strftime('%m/%d')} の休み希望が定員オーバーで割り当てできません")
                continue
                
            if date in user_assigned_dates[user.id]:
                continue

            key = (date, rest_pattern.id)
            shift = shift_dict.get(key)
            if not shift:
                shift = Shift.objects.create(date=date, team=user.team, pattern=rest_pattern)
                shift_map[date].append(shift)
                shift_dict[key] = shift

            if UserShift.objects.filter(user=user, shift=shift, is_manual=True).exists():
                continue

            assigned_pairs.append((user, shift))
            user_assigned_dates[user.id].add(date)
            user_shift_history[user.id][date] = '○'
            assigned_count_per_pattern[date][rest_pattern.id] += 1

   
    for date in sorted(shift_map.keys()):
        daily_shifts = shift_map[date]
        random.shuffle(daily_shifts)

        for shift in daily_shifts:
            pattern = shift.pattern
            if not pattern or pattern.id == rest_pattern.id:
                continue

            if assigned_count_per_pattern[date][pattern.id] >= pattern.max_people:
                errors.append(f"{date.strftime('%m/%d')} の {pattern.pattern_name} は定員を超えています")
                continue

            pattern_hours = calculate_hours(pattern.start_time, pattern.end_time)

            candidates = list(users)
            random.shuffle(candidates)
            candidates.sort(
                key=lambda u: (user_pattern_count[u.id][pattern.id], user_shift_count[u.id])
            )

            for user in candidates:
                if date in user_assigned_dates[user.id]:
                    continue
                if date in shift_requests.get(user.id, set()):
                    continue
                if UserShift.objects.filter(user=user, shift=shift, is_manual=True).exists():
                    continue

                week_start = date - timedelta(days=date.weekday())               
                if weekly_hours[user.id][week_start] >= 42:
                    errors.append(f"{user.name} の勤務時間が {week_start.strftime('%m/%d')}週で週40時間を超えています")
                    continue

            for user in candidates:
                if date in user_assigned_dates[user.id]:
                    continue
                if date in shift_requests.get(user.id, set()):
                    continue
                if UserShift.objects.filter(user=user, shift=shift, is_manual=True).exists():
                    continue

                week_start = date - timedelta(days=date.weekday())               
                if weekly_hours[user.id][week_start] >= 42:
                    continue

                consecutive_days = 0
                for i in range(1, 6):  
                    prev_day = date - timedelta(days=i)
                    val = user_shift_history[user.id].get(prev_day)
                    if val and val != '○':
                        consecutive_days += 1
                    else:
                        break
                if consecutive_days >= 5:
                    continue
              
                prev1 = user_shift_history[user.id].get(date - timedelta(days=1))
                prev2 = user_shift_history[user.id].get(date - timedelta(days=2))
                if prev1 == pattern.pattern_name and prev2 == pattern.pattern_name:
                    continue

                assigned_pairs.append((user, shift))
                user_assigned_dates[user.id].add(date)
                user_shift_count[user.id] += 1
                user_shift_history[user.id][date] = pattern.pattern_name
                weekly_hours[user.id][week_start] += pattern_hours
                assigned_count_per_pattern[date][pattern.id] += 1

                user_pattern_count[user.id][pattern.id] += 1

                if assigned_count_per_pattern[date][pattern.id] >= pattern.max_people:
                    break

   
    for user in users:
        for date in sorted(shift_map.keys()):
            if date in user_assigned_dates[user.id]:
                continue
            if assigned_count_per_pattern[date][rest_pattern.id] >= rest_pattern.max_people:
                continue

            week_start = date - timedelta(days=date.weekday())
            if weekly_hours[user.id][week_start] < 40:
                continue  

            key = (date, rest_pattern.id)
            shift = shift_dict.get(key)
            if not shift:
                shift = Shift.objects.create(date=date, team=user.team, pattern=rest_pattern)
                shift_map[date].append(shift)
                shift_dict[key] = shift

            if UserShift.objects.filter(user=user, shift=shift, is_manual=True).exists():
                continue

            assigned_pairs.append((user, shift))
            user_assigned_dates[user.id].add(date)
            user_shift_history[user.id][date] = '○'
            assigned_count_per_pattern[date][rest_pattern.id] += 1

    for user in users:
            current_rest_count = sum(1 for v in user_shift_history[user.id].values() if v == '○')
            needed_rest = max(0, 8 - current_rest_count)

            if needed_rest <= 0:
                continue

            for date in sorted(shift_map.keys()):
                if date in user_assigned_dates[user.id]:
                    continue
                if assigned_count_per_pattern[date][rest_pattern.id] >= rest_pattern.max_people:
                    continue

                key = (date, rest_pattern.id)
                shift = shift_dict.get(key)
                if not shift:
                    shift = Shift.objects.create(date=date, team=user.team, pattern=rest_pattern)
                    shift_map[date].append(shift)
                    shift_dict[key] = shift

                if UserShift.objects.filter(user=user, shift=shift, is_manual=True).exists():
                    continue

                assigned_pairs.append((user, shift))
                user_assigned_dates[user.id].add(date)
                user_shift_history[user.id][date] = '○'
                assigned_count_per_pattern[date][rest_pattern.id] += 1
                needed_rest -= 1

                if needed_rest <= 0:
                    break
    
    existing_user_shift_pairs = set(
        UserShift.objects.filter(shift__in=shifts).values_list('user_id', 'shift_id')
    )
    manual_pairs = set(
        UserShift.objects.filter(shift__in=shifts, is_manual=True).values_list('user_id', 'shift_id')
    )

    UserShift.objects.bulk_create([
        UserShift(user=user, shift=shift)
        for user, shift in assigned_pairs
        if (user.id, shift.id) not in existing_user_shift_pairs
        and (user.id, shift.id) not in manual_pairs
    ])

    return assigned_pairs, errors
