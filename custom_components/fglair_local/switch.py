"""Switches for yes/no properties that can be written."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FGLairConfigEntry
from .const import (
    CAP_COIL_DRY,
    CAP_ECO,
    CAP_MIN_HEAT,
    CAP_OUTDOOR_LOW_NOISE,
    CAP_POWERFUL,
    CAP_SWING_HORIZONTAL,
    CAP_SWING_VERTICAL,
)
from .coordinator import FGLairCoordinator
from .entity import FGLairEntity


@dataclass(frozen=True, kw_only=True)
class FGLairSwitchDescription(SwitchEntityDescription):
    capability: int | None = None


def _switch(key: str, capability: int | None = None) -> FGLairSwitchDescription:
    return FGLairSwitchDescription(key=key, translation_key=key, capability=capability)


def _unknown(key: str) -> FGLairSwitchDescription:
    """A property whose meaning is unconfirmed: off by default, under configuration."""
    return FGLairSwitchDescription(
        key=key,
        translation_key=key,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    )


SWITCHES = (
    _switch("economy_mode", CAP_ECO),
    _switch("powerful_mode", CAP_POWERFUL),
    _switch("min_heat", CAP_MIN_HEAT),
    _switch("outdoor_low_noise", CAP_OUTDOOR_LOW_NOISE),
    _switch("coil_dry_mode", CAP_COIL_DRY),
    _switch("af_vertical_swing", CAP_SWING_VERTICAL),
    _switch("af_horizontal_swing", CAP_SWING_HORIZONTAL),
    _unknown("indoor_fan_control"),
    _unknown("human_det_auto_off"),
    _unknown("human_det_auto_on_off"),
    _unknown("human_det_auto_save"),
    _unknown("master_timer_on_off_1"),
    _unknown("master_timer_on_off_2"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FGLairConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        FGLairSwitch(coordinator, description)
        for description in SWITCHES
        if description.key in coordinator.data
        and (description.capability is None or coordinator.has_capability(description.capability))
    )


class FGLairSwitch(FGLairEntity, SwitchEntity):
    """A setting that is on or off."""

    def __init__(
        self, coordinator: FGLairCoordinator, description: FGLairSwitchDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        value = self.coordinator.data.get(self.entity_description.key)
        return None if value is None else bool(value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.coordinator.write(self.entity_description.key, 1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.coordinator.write(self.entity_description.key, 0)
