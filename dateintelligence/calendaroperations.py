from datetime import datetime


class CalendarOperations:
    def add_months(self, since_date, months_to_add):
        day = since_date.day
        month = since_date.month
        year = since_date.year
        years_to_add = 0

        if months_to_add > 12:
            years_to_add = months_to_add // 12
            months_to_add = months_to_add % 12

        total_months = month + months_to_add

        if total_months > 12:
            years_to_add = years_to_add + 1
            total_months = total_months - 12

        if total_months == 2 and day > 28:
            day = 28

        if total_months in [4, 6, 9, 11] and day > 30:
            day = 30

        return datetime(year + years_to_add, total_months, day)

    def list_of_due_date(self, since_date, plan):
        return [self.add_months(since_date, x) for x in range(plan)]
