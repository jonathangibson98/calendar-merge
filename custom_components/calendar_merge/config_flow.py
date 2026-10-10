"""Config + options flow for Calendar Merge."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er, selector
from homeassistant.util import slugify

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


def _build_schema(include_name: bool, exclude: list[str] | None = None) -> vol.Schema:
    fields: dict[Any, Any] = {}
    if include_name:
        fields[vol.Required(CONF_NAME)] = selector.TextSelector()
    fields[vol.Required(CONF_CALENDARS)] = selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain="calendar", multiple=True, exclude_entities=exclude or []
        )
    )
    fields[vol.Required(CONF_DAYS_AHEAD, default=DEFAULT_DAYS_AHEAD)] = (
        selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1,
                max=365,
                step=1,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="days",
            )
        )
    )
    fields[vol.Required(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL)] = (
        selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=5,
                max=1440,
                step=1,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="min",
            )
        )
    )
    fields[vol.Required(CONF_DEDUPLICATE, default=DEFAULT_DEDUPLICATE)] = (
        selector.BooleanSelector()
    )
    return vol.Schema(fields)


def _clean_options(user_input: dict[str, Any]) -> dict[str, Any]:
    return {
        CONF_CALENDARS: list(user_input[CONF_CALENDARS]),
        CONF_DAYS_AHEAD: int(user_input[CONF_DAYS_AHEAD]),
        CONF_UPDATE_INTERVAL: int(user_input[CONF_UPDATE_INTERVAL]),
        CONF_DEDUPLICATE: bool(user_input[CONF_DEDUPLICATE]),
    }


class CalendarMergeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create a new merged calendar group. Run it again to make more groups."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> CalendarMergeOptionsFlow:
        return CalendarMergeOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            name = user_input[CONF_NAME].strip()
            if not name:
                errors["base"] = "no_name"
            elif not user_input[CONF_CALENDARS]:
                errors["base"] = "no_calendars"
            else:
                await self.async_set_unique_id(slugify(name))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=name, data={}, options=_clean_options(user_input)
                )

        schema = self.add_suggested_values_to_schema(
            _build_schema(include_name=True), user_input
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


class CalendarMergeOptionsFlow(OptionsFlow):
    """Change the calendars/settings of an existing group."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input[CONF_CALENDARS]:
                errors["base"] = "no_calendars"
            else:
                return self.async_create_entry(data=_clean_options(user_input))

        # Don't let a group pick itself as a source
        own = er.async_get(self.hass).async_get_entity_id(
            "calendar", DOMAIN, self.config_entry.entry_id
        )
        schema = self.add_suggested_values_to_schema(
            _build_schema(include_name=False, exclude=[own] if own else []),
            user_input or self.config_entry.options,
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
