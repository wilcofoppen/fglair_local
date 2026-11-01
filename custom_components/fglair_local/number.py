"""Numbers for writable integers whose unit and range are not documented."""

from __future__ import annotations

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FGLairConfigEntry
from .coordinator import FGLairCoordinator
from .entity import FGLairEntity


def _number(key: str) -> NumberEntityDescription:
    return NumberEntityDescription(
        key=key,
        translation_key=key,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        native_min_value=0,
        native_max_value=65535,
        native_step=1,
        mode=NumberMode.BOX,
    )


NUMBERS = (
    _number("auto_off_time"),
    _number("auto_on_off_time"),
    _number("auto_save_time"),
    _number("rc_prohibition"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FGLairConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        FGLairNumber(coordinator, description)
        for description in NUMBERS
        if description.key in coordinator.data
    )


class FGLairNumber(FGLairEntity, NumberEntity):
    """A plain integer setting."""

    def __init__(
        self, coordinator: FGLairCoordinator, description: NumberEntityDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get(self.entity_description.key)

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.write(self.entity_description.key, int(value))
