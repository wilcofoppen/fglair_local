"""Button to reset the filter sign."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FGLairConfigEntry
from .coordinator import FGLairCoordinator
from .entity import FGLairEntity

FILTER_RESET = ButtonEntityDescription(
    key="filter_sign_reset_display",
    translation_key="filter_sign_reset_display",
    entity_category=EntityCategory.CONFIG,
    entity_registry_enabled_default=False,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FGLairConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    if FILTER_RESET.key in coordinator.data:
        async_add_entities([FGLairFilterReset(coordinator)])


class FGLairFilterReset(FGLairEntity, ButtonEntity):
    """Writes 1 once; the unit clears the sign."""

    entity_description = FILTER_RESET

    def __init__(self, coordinator: FGLairCoordinator) -> None:
        super().__init__(coordinator, FILTER_RESET.key)

    async def async_press(self) -> None:
        self.coordinator.write(FILTER_RESET.key, 1)
