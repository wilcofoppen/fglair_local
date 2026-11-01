"""Base entity for FGLair Local."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FGLairCoordinator


class FGLairEntity(CoordinatorEntity[FGLairCoordinator]):
    """One entity bound to one property, or to the unit as a whole."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: FGLairCoordinator, key: str) -> None:
        super().__init__(coordinator)
        serial = coordinator.config_entry.unique_id
        data = coordinator.data
        self._attr_unique_id = f"{serial}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            manufacturer="Fujitsu General",
            model="AC-UTY",
            name=data.get("device_name") or coordinator.config_entry.title,
            serial_number=serial,
            sw_version=data.get("mcu_fw_version"),
        )

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.device.connected
