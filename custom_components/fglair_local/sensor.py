"""Sensors: temperatures, status and everything that can only be read."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FGLairConfigEntry
from .const import sensed_to_celsius
from .coordinator import FGLairCoordinator
from .entity import FGLairEntity


@dataclass(frozen=True, kw_only=True)
class FGLairSensorDescription(SensorEntityDescription):
    value_fn: Callable[[Any], Any] = lambda value: value


def _temperature(key: str, *, enabled: bool = True) -> FGLairSensorDescription:
    return FGLairSensorDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=sensed_to_celsius,
        entity_registry_enabled_default=enabled,
    )


def _diagnostic(key: str, *, enabled: bool = False) -> FGLairSensorDescription:
    return FGLairSensorDescription(
        key=key,
        translation_key=key,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=enabled,
    )


SENSORS = (
    _temperature("display_temperature"),
    _temperature("outdoor_temperature"),
    _diagnostic("error_code", enabled=True),
    _diagnostic("mcu_error", enabled=True),
    _diagnostic("op_status", enabled=True),
    _diagnostic("mcu_fw_version", enabled=True),
    _diagnostic("af_horizontal_num_dir"),
    _diagnostic("af_vertical_num_dir"),
    _diagnostic("auto_on_off_set_time"),
    _diagnostic("auto_save_set_time"),
    _diagnostic("building_name"),
    _diagnostic("comm_version"),
    _diagnostic("demand_control"),
    _diagnostic("device_capabilities"),
    _diagnostic("device_name"),
    _diagnostic("human_det"),
    _diagnostic("model_name"),
    _diagnostic("reboot_range"),
    _diagnostic("reboot_start"),
    _diagnostic("service_function_address"),
    _diagnostic("system_type"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FGLairConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        FGLairSensor(coordinator, description)
        for description in SENSORS
        if description.key in coordinator.data
    )


class FGLairSensor(FGLairEntity, SensorEntity):
    """A value that can only be read."""

    entity_description: FGLairSensorDescription

    def __init__(
        self, coordinator: FGLairCoordinator, description: FGLairSensorDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        value = self.coordinator.data.get(self.entity_description.key)
        return None if value is None else self.entity_description.value_fn(value)
