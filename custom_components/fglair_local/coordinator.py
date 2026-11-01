"""Coordinator: polls the module and passes on the values it pushes itself."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import ALL_PROPERTIES, DOMAIN, FAST_PROPERTIES, PROPERTY_TYPES
from .lan import AylaLanDevice

_LOGGER = logging.getLogger(__name__)

FULL_READ_TIMEOUT = 60
FAST_READ_TIMEOUT = 20
FULL_READ_SECONDS = 3600


class FGLairCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Holds the latest values of one air conditioner."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        device: AylaLanDevice,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {device.host}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.device = device
        self._full_read_every = max(FULL_READ_SECONDS // scan_interval, 1)
        self._polls = 0
        self._remove_listener = device.add_listener(self._on_values_changed)

    @callback
    def _on_values_changed(self) -> None:
        if self.data is not None:
            self.data = dict(self.device.values)
            self.async_update_listeners()

    def has_capability(self, bit: int) -> bool:
        capabilities = (self.data or {}).get("device_capabilities")
        return capabilities is None or bool(int(capabilities) >> bit & 1)

    def write(self, name: str, value: Any) -> None:
        """Queue a write; the value shows right away and is read back."""
        self.device.queue_write(name, value, PROPERTY_TYPES[name])

    def async_shutdown_listener(self) -> None:
        self._remove_listener()

    async def _async_update_data(self) -> dict[str, Any]:
        full_read = self._polls % self._full_read_every == 0
        names = ALL_PROPERTIES if full_read else FAST_PROPERTIES
        names = [name for name in names if name not in self.device.unreadable]
        result = await self.device.async_read(
            names, FULL_READ_TIMEOUT if full_read else FAST_READ_TIMEOUT
        )
        if not self.device.connected or not self.device.called_back:
            raise UpdateFailed(f"No connection with {self.device.host}")
        if not result:
            raise UpdateFailed(f"No values from {self.device.host}")
        self._polls += 1
        return dict(self.device.values)
