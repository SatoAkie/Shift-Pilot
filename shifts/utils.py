import random
from collections import defaultdict
from datetime import timedelta
from .models import UserShift

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

    for shift in shifts:
        shift_map[shift.date].append(shift)

    for date in sorted(shift_map.keys()):
        daily_shifts = shift_map[date]
        random.shuffle(daily_shifts)

        for shift in daily_shifts:
            pattern = shift.pattern
            if pattern is None:
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
                
    return [(u, s) for u, s in assigned_pairs if s is not None]
