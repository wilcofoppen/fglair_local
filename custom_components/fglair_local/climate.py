"""Climate entity: the main control of the air conditioner."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    PRESET_BOOST,
    PRESET_ECO,
    PRESET_NONE,
    SWING_BOTH,
    SWING_HORIZONTAL,
    SWING_OFF,
    SWING_VERTICAL,
    ATTR_HVAC_MODE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_HALVES, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FGLairConfigEntry
from .const import (
    CAP_AUTO,
    CAP_COOL,
    CAP_DRY,
    CAP_ECO,
    CAP_FAN,
    CAP_FAN_AUTO,
    CAP_FAN_HIGH,
    CAP_FAN_LOW,
    CAP_FAN_MEDIUM,
    CAP_FAN_QUIET,
    CAP_HEAT,
    CAP_POWERFUL,
    CAP_SWING_HORIZONTAL,
    CAP_SWING_VERTICAL,
    MAX_TEMP,
    MIN_TEMP_HEAT,
    MIN_TEMP_OTHER,
    MODE_AUTO,
    MODE_COOL,
    MODE_DRY,
    MODE_FAN,
    MODE_HEAT,
    MODE_OFF,
    MODE_ON,
    sensed_to_celsius,
)
from .coordinator import FGLairCoordinator
from .entity import FGLairEntity

FAN_QUIET = "quiet"

HVAC_TO_VALUE = {
    HVACMode.OFF: MODE_OFF,
    HVACMode.AUTO: MODE_AUTO,
    HVACMode.COOL: MODE_COOL,
    HVACMode.DRY: MODE_DRY,
    HVACMode.FAN_ONLY: MODE_FAN,
    HVACMode.HEAT: MODE_HEAT,
}
VALUE_TO_HVAC = {value: mode for mode, value in HVAC_TO_VALUE.items()}
HVAC_CAPABILITIES = {
    HVACMode.AUTO: CAP_AUTO,
    HVACMode.COOL: CAP_COOL,
    HVACMode.DRY: CAP_DRY,
    HVACMode.FAN_ONLY: CAP_FAN,
    HVACMode.HEAT: CAP_HEAT,
}
FAN_TO_VALUE = {FAN_QUIET: 0, FAN_LOW: 1, FAN_MEDIUM: 2, FAN_HIGH: 3, FAN_AUTO: 4}
VALUE_TO_FAN = {value: mode for mode, value in FAN_TO_VALUE.items()}
FAN_CAPABILITIES = {
    FAN_QUIET: CAP_FAN_QUIET,
    FAN_LOW: CAP_FAN_LOW,
    FAN_MEDIUM: CAP_FAN_MEDIUM,
    FAN_HIGH: CAP_FAN_HIGH,
    FAN_AUTO: CAP_FAN_AUTO,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FGLairConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([FGLairClimate(entry.runtime_data)])


class FGLairClimate(FGLairEntity, ClimateEntity):
    """The air conditioner itself."""

    _attr_name = None
    _attr_precision = PRECISION_HALVES
    _attr_target_temperature_step = 0.5
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_max_temp = MAX_TEMP

    def __init__(self, coordinator: FGLairCoordinator) -> None:
        super().__init__(coordinator, "climate")
        cap = coordinator.has_capability
        self._last_mode: int | None = None
        self._attr_hvac_modes = [
            HVACMode.OFF,
            *(mode for mode, bit in HVAC_CAPABILITIES.items() if cap(bit)),
        ]
        self._attr_fan_modes = [mode for mode, bit in FAN_CAPABILITIES.items() if cap(bit)]

        features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )
        self._vertical = cap(CAP_SWING_VERTICAL)
        self._horizontal = cap(CAP_SWING_HORIZONTAL)
        swing_modes = [SWING_OFF]
        if self._vertical:
            swing_modes.append(SWING_VERTICAL)
        if self._horizontal:
            swing_modes.append(SWING_HORIZONTAL)
        if self._vertical and self._horizontal:
            swing_modes.append(SWING_BOTH)
        if len(swing_modes) > 1:
            self._attr_swing_modes = swing_modes
            features |= ClimateEntityFeature.SWING_MODE

        self._eco = cap(CAP_ECO)
        self._boost = cap(CAP_POWERFUL)
        presets = [PRESET_NONE]
        if self._eco:
            presets.append(PRESET_ECO)
        if self._boost:
            presets.append(PRESET_BOOST)
        if len(presets) > 1:
            self._attr_preset_modes = presets
            features |= ClimateEntityFeature.PRESET_MODE
        self._attr_supported_features = features

    @property
    def _data(self) -> dict[str, Any]:
        return self.coordinator.data

    @property
    def hvac_mode(self) -> HVACMode | None:
        value = self._data.get("operation_mode")
        if value == MODE_ON:
            return HVACMode.AUTO
        if value not in (None, MODE_OFF):
            self._last_mode = value
        return VALUE_TO_HVAC.get(value)

    @property
    def current_temperature(self) -> float | None:
        value = self._data.get("display_temperature")
        return None if value is None else sensed_to_celsius(value)

    @property
    def target_temperature(self) -> float | None:
        value = self._data.get("adjust_temperature")
        return None if value is None else value / 10

    @property
    def min_temp(self) -> float:
        if self._data.get("operation_mode") == MODE_HEAT:
            return MIN_TEMP_HEAT
        return MIN_TEMP_OTHER

    @property
    def fan_mode(self) -> str | None:
        return VALUE_TO_FAN.get(self._data.get("fan_speed"))

    @property
    def swing_mode(self) -> str | None:
        vertical = bool(self._data.get("af_vertical_swing"))
        horizontal = bool(self._data.get("af_horizontal_swing"))
        if vertical and horizontal:
            return SWING_BOTH
        if vertical:
            return SWING_VERTICAL
        if horizontal:
            return SWING_HORIZONTAL
        return SWING_OFF

    @property
    def preset_mode(self) -> str | None:
        if self._boost and self._data.get("powerful_mode"):
            return PRESET_BOOST
        if self._eco and self._data.get("economy_mode"):
            return PRESET_ECO
        return PRESET_NONE

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        self.coordinator.write("operation_mode", HVAC_TO_VALUE[hvac_mode])

    async def async_turn_on(self) -> None:
        self.coordinator.write("operation_mode", self._last_mode or MODE_ON)

    async def async_turn_off(self) -> None:
        self.coordinator.write("operation_mode", MODE_OFF)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (hvac_mode := kwargs.get(ATTR_HVAC_MODE)) is not None:
            await self.async_set_hvac_mode(hvac_mode)
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is not None:
            self.coordinator.write("adjust_temperature", int(round(temperature * 2) * 5))

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        self.coordinator.write("fan_speed", FAN_TO_VALUE[fan_mode])

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        if self._vertical:
            self.coordinator.write(
                "af_vertical_swing", int(swing_mode in (SWING_VERTICAL, SWING_BOTH))
            )
        if self._horizontal:
            self.coordinator.write(
                "af_horizontal_swing", int(swing_mode in (SWING_HORIZONTAL, SWING_BOTH))
            )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if self._eco:
            self.coordinator.write("economy_mode", int(preset_mode == PRESET_ECO))
        if self._boost:
            self.coordinator.write("powerful_mode", int(preset_mode == PRESET_BOOST))
