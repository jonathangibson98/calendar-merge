"""Calendar Merge: combine several calendars into one."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import CalendarMergeConfigEntry, MergedCalendarCoordinator

PLATFORMS = [Platform.CALENDAR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: CalendarMergeConfigEntry) -> bool:
    """Set up one merged calendar group."""
    coordinator = MergedCalendarCoordinator(hass, entry)
    # Raises ConfigEntryNotReady if no source calendar can be read yet
    # (for example at startup), and Home Assistant will retry on its own.
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_change))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CalendarMergeConfigEntry) -> bool:
    """Unload a merged calendar group."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_on_change(hass: HomeAssistant, entry: CalendarMergeConfigEntry) -> None:
    """Reload when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
