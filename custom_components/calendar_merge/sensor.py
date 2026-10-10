"""Sensor for Calendar Merge: upcoming events as attributes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CalendarMergeConfigEntry, MergedCalendarCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CalendarMergeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([MergedCalendarSensor(entry.runtime_data, entry)])


class MergedCalendarSensor(CoordinatorEntity[MergedCalendarCoordinator], SensorEntity):
    """State = number of upcoming events. Attributes hold the full list."""

    _attr_has_entity_name = True
    _attr_name = "Upcoming events"
    _attr_icon = "mdi:calendar-multiple"
    _attr_native_unit_of_measurement = "events"
    # The event list can be big; keep it out of the database history.
    _unrecorded_attributes = frozenset({"events", "calendars"})

    def __init__(
        self, coordinator: MergedCalendarCoordinator, entry: CalendarMergeConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_upcoming"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Calendar Merge",
            model="Merged calendar",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data or [])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        events = []
        for m in self.coordinator.data or []:
            ev = m.event
            events.append(
                {
                    "summary": ev.summary,
                    "start": ev.start.isoformat(),
                    "end": ev.end.isoformat(),
                    "all_day": not isinstance(ev.start, datetime),
                    "description": ev.description or "",
                    "location": ev.location or "",
                    "calendar": m.source,
                }
            )
        last = self.coordinator.last_fetch
        return {
            "events": events,
            "event_count": len(events),
            "days_ahead": self.coordinator.days_ahead,
            "calendars": self.coordinator.calendars,
            "last_updated": last.isoformat() if last else None,
        }
