from dataclasses import dataclass
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple

from kalshi.rest import KalshiRestClient
from zoneinfo import ZoneInfo

# Temporary hours, which are found at https://help.kalshi.com/faq/what-are-trading-hours
TEMPORARY_HOURS = {
    "monday": (time(8, 0), time(3, 0)),
    "tuesday": (time(8, 0), time(3, 0)),
    "wednesday": (time(8, 0), time(3, 0)),
    "thursday": (time(8, 0), time(3, 0)),
    "friday": (time(8, 0), time(3, 0)),
    "saturday": (time(8, 0), time(3, 0)),
    "sunday": (time(8, 0), time(3, 0)),
}


@dataclass
class KalshiSchedule:
    """
    Represents the trading schedule for Kalshi. Including the trading hours and maintenance windows.

    Attributes:
        trading_hours (Dict[str, Tuple[time, time]]): Maps day names to (open_time, close_time).
        maintenance_windows (List[Tuple[datetime, datetime]]): List of maintenance windows as (start, end) time tuples.
        timezone (str): The timezone for the exchange, default is "UTC".
    """

    trading_hours: Dict[str, Tuple[time, time]]
    maintenance_windows: List[Tuple[datetime, datetime]]
    timezone: str = "UTC"

    @staticmethod
    def from_api(
        rest_client: KalshiRestClient,
        timezone: str = "UTC",
        override_hours: Optional[Dict[str, Tuple[time, time]]] = None,
    ):
        """
        Creates a `KalshiSchedule` from an API fetch.

        Attributes:
            rest_client (KalshiRestClient): An instance of the the KalshiRestClient. Used to fetch the current schedule and maintenance windows.
            timezone (str): Default "UTC". The timezone.
            override_hours (Optional[Dict[str, Tuple[time, time]]]): Override for trading hours derived from the API. Useful when the exchange is currently using temporary trading hours.

        Returns:
            KalshiSchedule: A new instance with the exchange schedule.
        """
        # Fetch the schedule from the API
        schedule = rest_client.get_exchange_schedule()

        # Parse maintenance windows
        maintenance_windows = [
            (
                datetime.fromisoformat(mw["start_dateime"].replace("Z", "+00:00")),
                datetime.fromisoformat(mw["end_dateime"].replace("Z", "+00:00")),
            )
            for mw in schedule.get("maintenance_windows", [])
        ]

        # If override hours are provided, use them
        if override_hours:
            trading_hours = override_hours
        else:
            trading_hours = {
                day.lower(): (
                    datetime.strptime(hours["open_time"], "%H%M").time(),
                    datetime.strptime(hours["close_time"], "%H%M").time(),
                )
                for day, hours in schedule["standard_hours"].items()
            }

        return KalshiSchedule(
            trading_hours=trading_hours,
            maintenance_windows=maintenance_windows,
            timezone=timezone,
        )

    @property
    def is_open(self, timestamp: Optional[datetime] = None) -> bool:
        """
        Determines if the exchange is open at the current time or at a specific timestamp if specified.

        Attributes:
            timestamp (Optional[datetime]): A dateime object representing a query time.

        Returns:
            bool: True if exchange is open, False if closed.
        """
        timestamp = timestamp or datetime.now(tz=ZoneInfo(self.timezone))
        local_time = timestamp.time()
        weekday_name = timestamp.strftime("%A").lower()

        if weekday_name not in self.trading_hours:
            return False

        open_time, close_time = self.trading_hours[weekday_name]

        if open_time < close_time:
            # Normal case where trading hours start and end on the same day
            return open_time <= local_time <= close_time

        else:
            # Trading hours that span over midnight
            return local_time >= open_time or local_time <= close_time

    @property
    def is_in_maintenance_window(self, timestamp: Optional[datetime] = None) -> bool:
        """
        Determines if the exchange is in a maintenance window at the current time or at a specific time if specified.

        Attributes:
            timestamp (Optional[datetime]): A datetime object representing a query time.

        Returns:
            bool: True if exchange is in maintenance window, False if not.
        """
        timestamp = timestamp or datetime.now(tz=ZoneInfo(self.timezone))
        return any(start <= timestamp <= end for start, end in self.maintenance_windows)

    def add_maintenance_window(self, start: datetime, end: datetime) -> None:
        """
        Adds to the list of maintenance windows.

        Attributes:
            start (datetime): The start datetime of the maintenance window.
            end (datetime): The end datetime of the maintenance window.
        """
        self.maintenance_windows.append((start, end))

    def get_trading_hours(self, weekday: Optional[str] = None) -> Tuple[time, time]:
        """
        Gets the trading hours for the current day or on a specific day if specified.

        Attributes:
            weekday (Optional[str]): The day of the week. Lowercase, full name of the day.

        Returns:
            Tuple[time, time]: The trading hours for the day.

        Raises:
            KeyError: If the specified weekday does not exist in trading_hours.
        """
        weekday = (
            weekday or datetime.now(tz=ZoneInfo(self.timezone)).strftime("%A").lower()
        )

        if weekday not in self.trading_hours:
            raise KeyError(f"Trading hours for {weekday} are not defined")

        return self.trading_hours[weekday]
