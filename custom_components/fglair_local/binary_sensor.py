"""Binary sensors for yes/no properties that cannot be written."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FGLairConfigEntry
from .coordinator import FGLairCoordinator
from .entity import FGLairEntity


def _diagnostic(key: str) -> BinarySensorEntityDescription:
    return BinarySensorEntityDescription(
        key=key,
        translation_key=key,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    )


# test_run is writable in the cloud, but shown read-only here: it starts the unit.
BINARY_SENSORS = (
    _diagnostic("child_lock_mode"),
    _diagnostic("test_run"),
    _diagnostic("wifi_led_enable"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FGLairConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        FGLairBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
        if description.key in coordinator.data
    )


class FGLairBinarySensor(FGLairEntity, BinarySensorEntity):
    """A yes/no value that can only be read."""

    def __init__(
        self, coordinator: FGLairCoordinator, description: BinarySensorEntityDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        value = self.coordinator.data.get(self.entity_description.key)
        return None if value is None else bool(value)
