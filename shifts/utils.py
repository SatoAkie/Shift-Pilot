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
    from collections import defaultdict
    from datetime import timedelta, date, datetime
    from .models import UserShift, ShiftPattern

    assigned_pairs = []
    shift_map = defaultdict(list)
    assigned_count = defaultdict(lambda: defaultdict(int))
    user_assigned_dates = defaultdict(set)
    user_shift_history = defaultdict(dict)

    for us in UserShift.objects.filter(user__in=users).select_related('shift__pattern', 'shift'):
        if us.shift and us.shift.pattern:
            user_shift_history[us.user.id][us.date] = us.shift.pattern.pattern_name
        else:
            user_shift_history[us.user.id][us.date] = '休'

        user_assigned_dates[us.user.id].add(us.date)

    weekly_hours = defaultdict(lambda: defaultdict(float))
    user_pattern_count = defaultdict(lambda: defaultdict(int))
    errors = []

    # Shift を日付ごとにまとめる
    for shift in shifts:
        shift_map[shift.date].append(shift)

    all_dates = sorted(shift_map.keys())

    # ① 希望休を先に反映
    for user in users:
        for day in shift_requests.get(user.id, set()):
            assigned_pairs.append(UserShift(
                user=user,
                shift=None,
                date=day,
                is_manual=False,
                is_error=False
            ))
            user_assigned_dates[user.id].add(day)
            user_shift_history[user.id][day] = '休'

    # ② 勤務を割り当てる
    for day in all_dates:
        shifts_today = shift_map[day]
        for shift in shifts_today:
            pattern = shift.pattern
            if not pattern:
                continue

            if assigned_count[day][pattern.id] >= pattern.max_people:
                errors.append(f"{day.strftime('%m/%d')} の {pattern.pattern_name} は定員オーバーです")
                continue

            candidates = list(users)
            random.shuffle(candidates)
            candidates.sort(key=lambda u: (user_pattern_count[u.id][pattern.id], len(user_assigned_dates[u.id])))

            for user in candidates:
                if day in user_assigned_dates[user.id]:
                    continue
                if UserShift.objects.filter(user=user, shift=shift, is_manual=True).exists():
                    continue

                # 週40時間制限チェック
                week_start = day - timedelta(days=day.weekday())
                if weekly_hours[user.id][week_start] >= 40:
                    continue

                # 連勤制限（最大5連勤）
                consecutive_days = [day - timedelta(days=i) for i in range(1, 6)]
                if all(user_shift_history[user.id].get(d) not in [None, '休'] for d in consecutive_days):
                    continue
                # 同一パターンの連続回避
                if user_shift_history[user.id].get(day - timedelta(days=1)) == pattern.pattern_name:
                    continue
                assigned_pairs.append(UserShift(
                    user=user,
                    shift=shift,
                    date=day,
                    is_manual=False,
                    is_error=False
                ))
                user_assigned_dates[user.id].add(day)
                user_shift_history[user.id][day] = pattern.pattern_name
                assigned_count[day][pattern.id] += 1
                user_pattern_count[user.id][pattern.id] += 1

                # 勤務時間（休憩1時間差引）
                total_minutes = (datetime.combine(date.today(), pattern.end_time) -
                                 datetime.combine(date.today(), pattern.start_time)).seconds // 60
                work_hours = max(0, (total_minutes - 60) / 60)
                weekly_hours[user.id][week_start] += work_hours

                if assigned_count[day][pattern.id] >= pattern.max_people:
                    break

    # ③ 残り日をエラーまたは休みで補完
    for day in all_dates:
        for user in users:
            if day in user_assigned_dates[user.id]:
                continue

            consecutive_work_days = 0
            for i in range(1, 6):
                d = day - timedelta(days=i)
                pattern_name = user_shift_history[user.id].get(d)
                if pattern_name not in [None, '休']:
                    consecutive_work_days += 1
                else:
                    break  # 途中に休みがあればカウント中断

            if consecutive_work_days >= 5:
                assigned_pairs.append(UserShift(
                    user=user,
                    shift=None,
                    date=day,
                    is_manual=False,
                    is_error=False  # 通常の休みとして扱う
                ))
                user_shift_history[user.id][day] = '休'
                user_assigned_dates[user.id].add(day)
                continue

            # 補完する休みは「エラー扱いにせず休みとして表示」
            assigned_pairs.append(UserShift(
                user=user,
                shift=None,
                date=day,
                is_manual=False,
                is_error=False  # ← すべて「正常な休み」として扱う
            ))
            user_shift_history[user.id][day] = '休'
            user_assigned_dates[user.id].add(day)


    return assigned_pairs, errors
