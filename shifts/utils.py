import random
from collections import defaultdict
from datetime import timedelta
from .models import UserShift

def assign_shifts(users, shifts, shift_requests):
    user_shift_count = defaultdict(int)
    shift_map = defaultdict(list)
    assigned_pairs = []

    for shift in shifts:
        shift_map[shift.date].append(shift)

    for date in sorted(shift_map.keys()):
        for shift in shift_map[date]:
            pattern = shift.pattern
            assigned = 0

            candidates = list(users)
            random.shuffle(candidates)
            candidates.sort(key=lambda u: user_shift_count[u.id])

            for user in candidates:
                if date in shift_requests.get(user.id, set()):
                    continue

                prev_shift= UserShift.objects.filter(user=user, shift__date=date - timedelta(days=1)).first()
                if prev_shift and prev_shift.shift.pattern_id == pattern.id:
                    continue

                streak = 0
                for i in range(1, 4):
                    prev_date = date - timedelta(days=i)
                    if UserShift.objects.filter(user=user, shift__date=prev_date).exists():
                        streak += 1
                    else:
                        break
                if streak >= 3:
                    continue

                assigned_pairs.append((user, shift))
                user_shift_count[user.id] += 1
                assigned += 1
                if assigned >= shift.pattern.max_people:
                    break
