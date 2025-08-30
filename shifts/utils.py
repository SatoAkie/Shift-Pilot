import random
from collections import defaultdict
from datetime import datetime, date, timedelta
from .models import UserShift, ShiftPattern, Shift

TARGET_REST_DAYS = 8 

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
    users_list = list(users)

    # ① 希望休を先に反映
    user_rest_count = {u.id: 0 for u in users_list} 
    for user in users_list:
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
            user_rest_count[user.id] += 1

    # 休みの補完（最低必要休 → 8日達成まで）
    # 各日の総枠と最低必要休を計算
    sum_capacity = {
        day: sum((sh.pattern.max_people if sh.pattern else 0) for sh in shift_map[day])
        for day in all_dates
    }
    min_rest_needed = {day: max(0, len(users_list) - sum_capacity[day]) for day in all_dates}

    # 最低必要休を補完（希望休を除外し、休が少ない人を優先）
    for day in all_dates:
        need = min_rest_needed[day]
        if need <= 0:
            continue
        candidates = [u for u in users_list
                      if day not in user_assigned_dates[u.id]
                      and day not in shift_requests.get(u.id, set())]
        # 休が少ない人優先
        candidates.sort(key=lambda u: (user_rest_count[u.id], len(user_assigned_dates[u.id])))
        for u in candidates[:need]:
            assigned_pairs.append(UserShift(user=u, shift=None, date=day,
                                            is_manual=False, is_error=False))
            user_assigned_dates[u.id].add(day)
            user_shift_history[u.id][day] = '休'
            user_rest_count[u.id] += 1

    days_cycle = list(all_dates)
    
    # 人ごとに休の少ない順で回す
    for u in sorted(users_list, key=lambda x: user_rest_count[x.id]):
        while user_rest_count[u.id] < TARGET_REST_DAYS:
            placed = False
            for day in days_cycle:
                if day in user_assigned_dates[u.id]:
                    continue
                rests_today = sum(
                    1 for x in users_list
                    if user_shift_history[x.id].get(day) == '休'
                )
                # 全員休みにしない
                if sum_capacity.get(day, 0) > 0 and rests_today + 1 >= len(users_list):
                    continue

                assigned_pairs.append(UserShift(
                    user=u,
                    shift=None,
                    date=day,
                    is_manual=False,
                    is_error=False
                ))
                user_assigned_dates[u.id].add(day)
                user_shift_history[u.id][day] = '休'
                user_rest_count[u.id] += 1
                placed = True
                break  # ← for day

            if not placed:
                break  # ← while

        
    # ② 勤務を割り当てる
    for day in all_dates:
        shifts_today = shift_map[day]
        for shift in shifts_today:
            pattern = shift.pattern
            if not pattern:
                continue

            if assigned_count[day][pattern.id] >= pattern.max_people:
                continue

            candidates = list(users_list)
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


        # 日ごとの空き枠有無を計算
    day_has_free_capacity = {}
    for day in all_dates:
        free = False
        for sh in shift_map[day]:
            pat = sh.pattern
            if not pat:
                continue
            if assigned_count[day][pat.id] < pat.max_people:
                free = True
                break
        day_has_free_capacity[day] = free

    def user_can_take_any_shift(user, day):
        week_start = day - timedelta(days=day.weekday())
        if weekly_hours[user.id][week_start] >= 40:
            return False
        for sh in shift_map[day]:
            pat = sh.pattern
            if not pat:
                continue
            if assigned_count[day][pat.id] >= pat.max_people:
                continue
            if user_shift_history[user.id].get(day - timedelta(days=1)) == pat.pattern_name:
                continue
            if UserShift.objects.filter(user=user, shift=sh, is_manual=True).exists():
                continue
            return True
        return False

    # ③ 残り日をエラーまたは休みで補完（順序を微調整）
    any_assignment_error = False

    for day in all_dates:
        for user in users_list:
            if day in user_assigned_dates[user.id]:
                continue

            # 直近5日がすべて勤務なら強制休み（通常休み扱い）
            consecutive_work_days = 0
            for i in range(1, 6):
                d = day - timedelta(days=i)
                pattern_name = user_shift_history[user.id].get(d)
                if pattern_name not in [None, '休']:
                    consecutive_work_days += 1
                else:
                    break
            if consecutive_work_days >= 5:
                assigned_pairs.append(UserShift(user=user, shift=None, date=day,
                                                is_manual=False, is_error=False))
                user_shift_history[user.id][day] = '休'
                user_assigned_dates[user.id].add(day)
                user_rest_count[user.id] = user_rest_count.get(user.id, 0) + 1
                continue

            # 容量満杯（空き枠なし） → 休（非エラー）
            if not day_has_free_capacity.get(day, False):
                assigned_pairs.append(UserShift(user=user, shift=None, date=day,
                                                is_manual=False, is_error=False))
                user_shift_history[user.id][day] = '休'
                user_assigned_dates[user.id].add(day)
                user_rest_count[user.id] = user_rest_count.get(user.id, 0) + 1
                continue

            # 個人規制で当日の全パターンに入れられない → 未（エラー）
            week_start = day - timedelta(days=day.weekday())
            if weekly_hours[user.id][week_start] >= 40 or not user_can_take_any_shift(user, day):
                assigned_pairs.append(UserShift(user=user, shift=None, date=day,
                                                is_manual=False, is_error=True))
                user_shift_history[user.id][day] = '休'  # 非勤務として連勤カウントは切る
                user_assigned_dates[user.id].add(day)
                any_assignment_error = True
                continue

            # それ以外（補完休） → 休（非エラー）
            assigned_pairs.append(UserShift(user=user, shift=None, date=day,
                                            is_manual=False, is_error=False))
            user_shift_history[user.id][day] = '休'
            user_assigned_dates[user.id].add(day)
            user_rest_count[user.id] = user_rest_count.get(user.id, 0) + 1

    if any_assignment_error:
        errors.append("勤務が一部割り当てられませんでした")

    return assigned_pairs, errors
