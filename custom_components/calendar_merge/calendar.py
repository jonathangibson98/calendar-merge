"""Calendar entity for Calendar Merge."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import (
    CalendarMergeConfigEntry,
    MergedCalendarCoordinator,
    as_datetime,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CalendarMergeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([MergedCalendarEntity(entry.runtime_data, entry)])


class MergedCalendarEntity(CoordinatorEntity[MergedCalendarCoordinator], CalendarEntity):
    """One merged calendar. Works with any calendar card."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self, coordinator: MergedCalendarCoordinator, entry: CalendarMergeConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Calendar Merge",
            model="Merged calendar",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def event(self) -> CalendarEvent | None:
        """The current event, or the next one if nothing is happening now."""
        now = dt_util.now()
        for merged in self.coordinator.data or []:
            if as_datetime(merged.event.end) > now:
                return merged.event
        return None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Events for any range (this is what calendar cards ask for)."""
        try:
            merged = await self.coordinator.async_fetch(start_date, end_date)
        except UpdateFailed:
            return []
        return [m.event for m in merged]
