from calendar import monthrange
from datetime import date, timedelta


def anniversary(anchor, months):
    total = anchor.year * 12 + anchor.month - 1 + months
    year, month_index = divmod(total, 12)
    month = month_index + 1
    return date(year, month, min(anchor.day, monthrange(year, month)[1]))


def period_for_date(anchor, current):
    months = max(0, (current.year - anchor.year) * 12 + current.month - anchor.month)
    if anniversary(anchor, months) > current and months:
        months -= 1
    return anniversary(anchor, months), anniversary(anchor, months + 1) - timedelta(days=1)


def billable_days(start, end, trial_end=None, service_end=None):
    first = max(start, trial_end + timedelta(days=1)) if trial_end else start
    last = min(end, service_end) if service_end else end
    return max(0, (last - first).days + 1)