import random
from collections import defaultdict
from datetime import timedelta
from .models import UserShift,ShiftPattern, Shift

def assign_shifts(users, shifts, shift_requests):
    
    user_shift_count = defaultdict(int)
    shift_map = defaultdict(list)
    assigned_pairs = []
    assigned_count_per_pattern = defaultdict(lambda: defaultdict(int))

    user_assigned_dates = defaultdict(set)

    existing_pairs = set(
        UserShift.objects.filter(shift__in=shifts)
        .values_list('user_id' , 'shift_id')
    )

    shift_dict = {}
    for shift in shifts:
        shift_map[shift.date].append(shift)
        if shift.pattern:
            shift_dict[(shift.date, shift.pattern.id)] = shift

    try:
        rest_pattern = ShiftPattern.objects.get(pattern_name = '○')
    except ShiftPattern.DoesNotExist:
        rest_pattern = None

    if rest_pattern:
        user_rest_count = defaultdict(int)

        for user in users:
            rest_dates = shift_requests.get(user.id, set())
            for date in rest_dates:
                if date in user_assigned_dates[user.id]:
                    continue
                if assigned_count_per_pattern[date][rest_pattern.id] >= rest_pattern.max_people:
                    continue
                
                key = (date, rest_pattern.id)
                rest_shift = shift_dict.get(key)
                if not rest_shift:
                    rest_shift = Shift.objects.create(date=date, team=user.team, pattern=rest_pattern)
                    shift_map[date].append(rest_shift)
                    shift_dict[key] = rest_shift

                if (user.id, rest_shift.id) not in existing_pairs:
                    UserShift.objects.get_or_create(user=user, shift=rest_shift)

                user_assigned_dates[user.id].add(date)
                user_rest_count[user.id] += 1
                assigned_count_per_pattern[date][rest_pattern.id] += 1

        for user in users:
            current_rest = user_rest_count[user.id]
            remaining = 8 - current_rest
            if remaining <= 0:
                continue

            candidates_dates =[
                date for date in sorted(shift_map.keys())
                if date not in user_assigned_dates[user.id] and
                    assigned_count_per_pattern[date][rest_pattern.id] < rest_pattern.max_people
                
            ]
            chosen_dates = random.sample(candidates_dates, min(remaining, len(candidates_dates)))

            for date in chosen_dates:
                key = (date, rest_pattern.id)
                rest_shift = shift_dict.get(key)
                if not rest_shift:
                    rest_shift = Shift.objects.create(date=date, team=user.team, pattern=rest_pattern)
                    shift_map[date].append(rest_shift)
                    shift_dict[key] = rest_shift

                if (user.id, rest_shift.id) not in existing_pairs:
                    UserShift.objects.get_or_create(user=user, shift=rest_shift)

                user_assigned_dates[user.id].add(date)
                assigned_count_per_pattern[date][rest_pattern.id] += 1

    for date in sorted(shift_map.keys()):
        daily_shifts = shift_map[date]
        random.shuffle(daily_shifts)

        for shift in daily_shifts:
            pattern = shift.pattern
            if pattern is None or (rest_pattern and pattern.id == rest_pattern.id):
                continue

            if assigned_count_per_pattern[date][pattern.id] >= pattern.max_people:
                continue

            candidates = list(users)
            random.shuffle(candidates)
            candidates.sort(key=lambda u: user_shift_count[u.id])

            for user in candidates:
                if date in user_assigned_dates[user.id]:
                    continue
                if (user.id, shift.id) in existing_pairs:       
                    continue
                if date in shift_requests.get(user.id, set()):               
                    continue

                prev_shift= UserShift.objects.filter(user=user, shift__date=date - timedelta(days=1)).first()
                if prev_shift and prev_shift.shift.pattern_id == pattern.id:              
                    continue

                streak = 0
                for i in range(1, 5):
                    prev_date = date - timedelta(days=i)
                    prev_us =  UserShift.objects.filter(user=user, shift__date=prev_date).select_related('shift__pattern').first()
                    if prev_us and prev_us.shift.pattern.pattern_name != '休み':
                        streak += 1
                    else:
                        break
                if streak >= 4:
                    continue
                       
                assigned_pairs.append((user, shift))
                user_shift_count[user.id] += 1
                assigned_count_per_pattern[date][pattern.id] += 1
                
                user_assigned_dates[user.id].add(date)
                
                if assigned_count_per_pattern[date][pattern.id] >= shift.pattern.max_people:
                    break
                
    existing_user_shift_pairs = set(
        UserShift.objects.filter(shift__in=shifts)
        .values_list('user_id','shift_id')
    )

    UserShift.objects.bulk_create([
        UserShift(user=user, shift=shift)
        for user, shift in assigned_pairs
        if (user.id, shift.id) not in existing_user_shift_pairs
    ])

    UserShift.objects.get_or_create(user=user, shift=rest_shift)


    return [(u, s) for u, s in assigned_pairs if s is not None]
