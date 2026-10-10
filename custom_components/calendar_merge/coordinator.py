"""Data coordinator for Calendar Merge."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import logging
from typing import Any

from homeassistant.components.calendar import CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CALENDARS,
    CONF_DAYS_AHEAD,
    CONF_DEDUPLICATE,
    CONF_UPDATE_INTERVAL,
    DEFAULT_DAYS_AHEAD,
    DEFAULT_DEDUPLICATE,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class MergedEvent:
    """An event plus the calendar entity it came from."""

    event: CalendarEvent
    source: str


def as_datetime(value: date | datetime) -> datetime:
    """Turn a date or datetime into an aware datetime (for sorting/comparing)."""
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, time.min, tzinfo=dt_util.get_default_time_zone())


def _parse_when(value: Any) -> date | datetime | None:
    """Parse a start/end value from a calendar.get_events response."""
    if isinstance(value, datetime):
        if value.tzinfo:
            return dt_util.as_local(value)
        return value.replace(tzinfo=dt_util.get_default_time_zone())
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value:
        return None
    if len(value) > 10:  # has a time part
        parsed = dt_util.parse_datetime(value)
        if parsed is None:
            return None
        if parsed.tzinfo:
            return dt_util.as_local(parsed)
        return parsed.replace(tzinfo=dt_util.get_default_time_zone())
    return dt_util.parse_date(value)


def _build_event(raw: dict[str, Any], source: str) -> MergedEvent | None:
    """Build a MergedEvent from one raw event dict."""
    start = _parse_when(raw.get("start"))
    if start is None:
        return None
    end = _parse_when(raw.get("end"))
    if end is None:
        end = start if isinstance(start, datetime) else start + timedelta(days=1)
    try:
        event = CalendarEvent(
            start=start,
            end=end,
            summary=raw.get("summary") or "No Title",
            description=raw.get("description") or None,
            location=raw.get("location") or None,
        )
    except ValueError:
        return None
    return MergedEvent(event=event, source=source)


class MergedCalendarCoordinator(DataUpdateCoordinator[list[MergedEvent]]):
    """Fetches and merges events from the chosen source calendars."""

    config_entry: CalendarMergeConfigEntry

    def __init__(self, hass: HomeAssistant, entry: CalendarMergeConfigEntry) -> None:
        options = entry.options
        self.calendars: list[str] = list(options.get(CONF_CALENDARS, []))
        self.days_ahead = int(options.get(CONF_DAYS_AHEAD, DEFAULT_DAYS_AHEAD))
        self.deduplicate = bool(options.get(CONF_DEDUPLICATE, DEFAULT_DEDUPLICATE))
        interval = int(options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
        self.last_fetch: datetime | None = None
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=timedelta(minutes=interval),
        )

    async def _async_update_data(self) -> list[MergedEvent]:
        now = dt_util.now()
        events = await self.async_fetch(now, now + timedelta(days=self.days_ahead))
        self.last_fetch = now
        return events

    async def async_fetch(self, start: datetime, end: datetime) -> list[MergedEvent]:
        """Fetch + merge events for any date range."""
        results = await asyncio.gather(
            *(self._fetch_one(cal, start, end) for cal in self.calendars)
        )
        succeeded = [r for r in results if r is not None]
        if self.calendars and not succeeded:
            raise UpdateFailed("None of the source calendars could be read")

        merged = [m for chunk in succeeded for m in chunk]

        if self.deduplicate:
            seen: set[tuple] = set()
            unique: list[MergedEvent] = []
            for m in merged:
                key = (m.event.summary.strip().lower(), m.event.start, m.event.end)
                if key in seen:
                    continue
                seen.add(key)
                unique.append(m)
            merged = unique

        merged.sort(key=lambda m: (as_datetime(m.event.start), m.event.summary))
        return merged

    async def _fetch_one(
        self, entity_id: str, start: datetime, end: datetime
    ) -> list[MergedEvent] | None:
        """Read one source calendar. Returns None if it could not be read."""
        try:
            response = await self.hass.services.async_call(
                "calendar",
                "get_events",
                {
                    "entity_id": entity_id,
                    "start_date_time": start,
                    "end_date_time": end,
                },
                blocking=True,
                return_response=True,
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Could not read calendar %s: %s", entity_id, err)
            return None

        data = (response or {}).get(entity_id)
        if not isinstance(data, dict):
            _LOGGER.warning("No data returned for calendar %s", entity_id)
            return None

        out: list[MergedEvent] = []
        for raw in data.get("events", []):
            built = _build_event(raw, entity_id)
            if built:
                out.append(built)
        return out


type CalendarMergeConfigEntry = ConfigEntry[MergedCalendarCoordinator]
