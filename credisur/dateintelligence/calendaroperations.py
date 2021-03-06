from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class CalendarOperations:
    def add_months(self, since_date, months_to_add):

        if not isinstance(since_date, datetime):
            raise ValueError("since_date is not a datetime object")

        if not isinstance(months_to_add, int):
            raise ValueError("months_to_add is not an integer")

        day = since_date.day
        month = since_date.month
        year = since_date.year
        years_to_add = 0
        add_months = months_to_add

        if months_to_add > 12:
            years_to_add = months_to_add // 12
            add_months = months_to_add % 12

        total_months = month + add_months

        if total_months > 12:
            years_to_add = years_to_add + 1
            total_months = total_months - 12

        if total_months == 2 and day > 28:
            day = 28

        if total_months in [4, 6, 9, 11] and day > 30:
            day = 30

        return datetime(year + years_to_add, total_months, day)

    def last_day_of_month(self, date_of_month=datetime.now()):
        next_month = self.add_months(date_of_month, 1)
        first_day_of_next_month = datetime(next_month.year, next_month.month, 1)
        return first_day_of_next_month + timedelta(days=-1)

    def first_day_of_month(self, date_of_month=datetime.now()):
        return datetime(date_of_month.year, date_of_month.month, 1)

    def first_day_of_last_month(self,date_of_month=datetime.now()):         
        d = date_of_month - relativedelta(months=1)
        return datetime(d.year, d.month, 1)

    def list_of_due_date(self, since_date, plan):
        return [self.add_months(since_date, x) for x in range(plan)]

