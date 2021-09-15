from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from datetime import timedelta, datetime
from typing import (
    Union,
    List,
)


class DateTimeRange:
    """
    A class to represent a range between a start date and an end date,
    that can be compared to other DateTimeRange objects using operands.

    Can be instantiated with either ISO 8601 strings or datetime objects

    Usage::
        # Overlapping DateRanges added together are merged into one DateTimeRange
        (
            DateTimeRange('2021-01-01T01:00:00', '2021-01-01T02:00:00') +
            DateTimeRange('2021-01-01T01:30:00', '2021-01-01T03:00:00')
        ) == DateTimeRange('2021-01-01T01:00:00', '2021-01-01T03:00:00')

        # Subtracting a DateTimeRange will remove the overlapping section
        (
            DateTimeRange('2021-01-01T01:00:00', '2021-01-01T02:00:00') -
            DateTimeRange('2021-01-01T01:30:00', '2021-01-01T03:00:00')
        ) == DateTimeRange('2021-01-01T01:00:00', '2021-01-01T01:30:00')

        # Non-overlapping DateRanges added together become a DateTimeRangeSequence
        (
            DateTimeRange('2021-01-01T01:00:00', '2021-01-01T02:00:00') +
            DateTimeRange('2021-01-01T03:00:00', '2021-01-01T04:00:00')
        ) == DateTimeRangeSequence(
            DateTimeRange('2021-01-01T01:00:00', '2021-01-01T02:00:00'),
            DateTimeRange('2021-01-01T03:00:00', '2021-01-01T04:00:00'),
        )

        # Subtracting can also return DateTimeRangeSequence
        (
            DateTimeRange('2021-01-01T01:00:00', '2021-01-01T04:00:00') -
            DateTimeRange('2021-01-01T02:00:00', '2021-01-01T03:00:00')
        ) == DateTimeRangeSequence(
            DateTimeRange('2021-01-01T01:00:00', '2021-01-01T02:00:00'),
            DateTimeRange('2021-01-01T03:00:00', '2021-01-01T04:00:00'),
        )

    Subtracting a DateTimeRange by a non-overlapping DateTimeRange will have no effect
    Adding or subtracting DateTimeRangeSequences will result in the same behavior
    """

    def __init__(self, start: Union[str, datetime], end: Union[str, datetime]) -> None:
        if isinstance(start, str):
            start = datetime.fromisoformat(start)
        if isinstance(end, str):
            end = datetime.fromisoformat(end)
        if end < start:
            raise ValueError(
                "DateTimeRange.start must be earlier than DateTimeRange.end"
            )
        self.start = start
        self.end = end

    def difference(
        self, other: Union[DateTimeRange, DateTimeRangeSequence]
    ) -> timedelta:
        """
        Returns the total non-overlapping duration
        """
        return (self - other).duration + (other - self).duration

    @property
    def duration(self) -> timedelta:
        return self.end - self.start

    def __add__(
        self, other: Union[DateTimeRange, DateTimeRangeSequence]
    ) -> Union[DateTimeRange, DateTimeRangeSequence]:
        if isinstance(other, (DateTimeRange, DateTimeRangeSequence)):
            date_time_ranges = _reduce_date_time_range_list([self, other])
            if len(date_time_ranges) == 1:
                return date_time_ranges[0]
            else:
                return DateTimeRangeSequence(*date_time_ranges)

        raise TypeError(
            f"unsupported operand type(s) for +: '{self.__class__}' and '{other.__class__}'"
        )

    def __sub__(
        self, other: Union[DateTimeRange, DateTimeRangeSequence]
    ) -> Union[DateTimeRange, DateTimeRangeSequence]:
        if isinstance(other, DateTimeRange):
            if (
                self.end <= other.start
                or other.end <= self.start
                or other.duration == timedelta(0)
            ):
                return self
            if other.start <= self.start:
                if self.end <= other.end:
                    # self is fully encapsulated within other,
                    # return an empty DateTimeRangeSequence
                    return DateTimeRangeSequence()
                else:
                    return DateTimeRange(other.end, self.end)
            else:
                if self.end <= other.end:
                    return DateTimeRange(self.start, other.start)
                else:
                    # other is fully encapsulated within self,
                    # take a slice out of the middle
                    return DateTimeRangeSequence(
                        DateTimeRange(self.start, other.start),
                        DateTimeRange(other.end, self.end),
                    )

        if isinstance(other, DateTimeRangeSequence):
            result = deepcopy(self)
            for date_time_range in other.date_time_ranges:
                result -= date_time_range
            return result

        raise TypeError(
            f"unsupported operand type(s) for -: '{self.__class__}' and '{other.__class__}'"
        )

    def __eq__(self, other: Union[DateTimeRange, DateTimeRangeSequence]) -> bool:
        if isinstance(other, DateTimeRange):
            if self.start == other.start and self.end == other.end:
                return True
            return False
        if isinstance(other, DateTimeRangeSequence):
            if len(other.date_time_ranges) and self == other.date_time_ranges[0]:
                return True
            return False
        raise TypeError(
            f"unsupported operand type(s) for =: '{self.__class__}' and '{other.__class__}'"
        )

    def __repr__(self) -> str:
        return (
            "<{self.__class__.__name__}"
            " start={self.start}"
            " end={self.end}"
            " duration={self.duration}"
            ">"
        ).format(self=self)


class DateTimeRangeSequence(Sequence):
    """
    A class to represent a sequence of DateTimeRange objects.

    This is an immutable 'list' object so len(object), list(object), and object[0]
    all work as expected.

    Use operands with other DateTimeRange or DateTimeRangeSequence objects to mutate the
    DateRanges in the sequence

    Can be instantiated with either a list DateTimeRange objects or ISO 8601 strings

    Usage::
        # Overlapping DateTimeRanges will automatically be joined
        # just like adding two DateTimeRanges together
        date_time_range_group = DateTimeRangeSequence(
            ('2021-01-01T01:00:00', '2021-01-01T02:00:00'),
            ('2021-01-01T03:00:00', '2021-01-01T04:00:00'),
            ('2021-01-01T03:30:00', '2021-01-01T04:30:00'),
        ) == DateTimeRangeSequence(
            ('2021-01-01T01:00:00', '2021-01-01T02:00:00'),
            ('2021-01-01T03:00:00', '2021-01-01T04:30:00'),
        )

        # A DateTimeRangeSequence with a single DateTimeRange is functionally equivalent
        # to a DateTimeRange
        DateTimeRangeSequence(
            DateTimeRange('2021-01-01T01:00:00', '2021-01-01T02:00:00')
        ) == DateTimeRange('2021-01-01T01:00:00', '2021-01-01T02:00:00')

    You can use all operands the with DateTimeRangeSequence the same as you can with DateTimeRanges
    You can add or subtract DateTimeRangeSequences together with DateTimeRanges and vice versa
    """

    def __init__(self, *date_time_ranges):
        self._date_time_ranges = None
        self.date_time_ranges = date_time_ranges

    def difference(
        self, other: Union[DateTimeRange, DateTimeRangeSequence]
    ) -> timedelta:
        """
        Returns the total non-overlapping duration
        """
        return (self - other).duration + (other - self).duration

    @property
    def date_time_ranges(self) -> List[DateTimeRange]:
        return self._date_time_ranges

    @date_time_ranges.setter
    def date_time_ranges(self, date_time_ranges: tuple) -> None:
        date_time_ranges = list(deepcopy(date_time_ranges))
        for i, date_time_range in enumerate(date_time_ranges):
            if not isinstance(date_time_range, DateTimeRange) and isinstance(
                date_time_range, (list, tuple)
            ):
                date_time_ranges[i] = DateTimeRange(
                    date_time_range[0], date_time_range[1]
                )

        self._date_time_ranges = sorted(
            _reduce_date_time_range_list(date_time_ranges), key=lambda x: x.start
        )

    @property
    def start(self) -> datetime:
        if self:
            return min([date_time_range.start for date_time_range in self])

    @property
    def end(self) -> datetime:
        if self:
            return max([date_time_range.end for date_time_range in self])

    @property
    def duration(self) -> timedelta:
        return sum([date_time_range.duration for date_time_range in self], timedelta())

    def __add__(
        self, other: Union[DateTimeRange, DateTimeRangeSequence]
    ) -> DateTimeRangeSequence:
        if isinstance(other, DateTimeRange):
            other_date_time_ranges = [other]
        elif isinstance(other, DateTimeRangeSequence):
            other_date_time_ranges = other.date_time_ranges
        else:
            raise TypeError(
                f"unsupported operand type(s) for +: '{self.__class__}' and '{other.__class__}'"
            )

        return DateTimeRangeSequence(*(self.date_time_ranges + other_date_time_ranges))

    def __sub__(
        self, other: Union[DateTimeRange, DateTimeRangeSequence]
    ) -> DateTimeRangeSequence:
        date_time_range_group = DateTimeRangeSequence()

        if isinstance(other, DateTimeRange):
            for date_time_range in self.date_time_ranges:
                date_time_range_group += date_time_range - other
        elif isinstance(other, DateTimeRangeSequence):
            for date_time_range in deepcopy(self.date_time_ranges):
                for other_date_time_range in other.date_time_ranges:
                    date_time_range -= other_date_time_range
                date_time_range_group += date_time_range
        else:
            raise TypeError(
                f"unsupported operand type(s) for -: '{self.__class__}' and '{other.__class__}'"
            )

        return date_time_range_group

    def __eq__(self, other: Union[DateTimeRange, DateTimeRangeSequence]) -> bool:
        if isinstance(other, DateTimeRange):
            other_date_time_ranges = [other]
        elif isinstance(other, DateTimeRangeSequence):
            other_date_time_ranges = other.date_time_ranges
        else:
            raise TypeError(
                f"unsupported operand type(s) for =: '{self.__class__}' and '{other.__class__}'"
            )

        if self.date_time_ranges == other_date_time_ranges:
            return True
        return False

    def __getitem__(self, key: int) -> DateTimeRange:
        return self.date_time_ranges[key]

    def __len__(self) -> int:
        return len(self.date_time_ranges)

    def __repr__(self) -> str:
        return (
            "<{self.__class__.__name__}"
            " start={self.start}"
            " end={self.end}"
            " duration={self.duration}"
            " date_time_ranges={self.date_time_ranges}"
            ">"
        ).format(self=self)


def _reduce_date_time_range_list(
    date_time_ranges: List[DateTimeRange],
) -> List[DateTimeRange]:
    if len(date_time_ranges) <= 1:
        return deepcopy(date_time_ranges)

    output = []
    date_time_ranges = sorted(
            deepcopy(date_time_ranges),
            key=lambda dtr: (dtr.start, dtr.end),
            reverse=True,
    )

    prev_dtr = date_time_ranges.pop()
    dtr = date_time_ranges.pop()
    while True:
        if dtr.start <= prev_dtr.end:
            prev_dtr = DateTimeRange(prev_dtr.start, max(dtr.end, prev_dtr.end))
        else:
            output.append(prev_dtr)
            prev_dtr = dtr

        try:
            dtr = date_time_ranges.pop()
        except IndexError:
            output.append(prev_dtr)
            break

    return output
