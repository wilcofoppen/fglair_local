"""Selects for the fixed vane positions."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FGLairConfigEntry
from .coordinator import FGLairCoordinator
from .entity import FGLairEntity

VANES = {
    "af_vertical_direction": "af_vertical_num_dir",
    "af_horizontal_direction": "af_horizontal_num_dir",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FGLairConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        FGLairVane(coordinator, key, int(coordinator.data[count_key]))
        for key, count_key in VANES.items()
        if coordinator.data.get(count_key)
    )


class FGLairVane(FGLairEntity, SelectEntity):
    """One position out of the number the unit reports."""

    def __init__(self, coordinator: FGLairCoordinator, key: str, positions: int) -> None:
        super().__init__(coordinator, key)
        self.entity_description = SelectEntityDescription(key=key, translation_key=key)
        self._attr_options = [str(position) for position in range(1, positions + 1)]

    @property
    def current_option(self) -> str | None:
        option = str(self.coordinator.data.get(self.entity_description.key))
        return option if option in self.options else None

    async def async_select_option(self, option: str) -> None:
        self.coordinator.write(self.entity_description.key, int(option))
