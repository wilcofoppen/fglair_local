"""Config flow: IP address plus LAN key, typed in or fetched from FGLair on the spot.

The LAN key is deliberately a plain text field, here and in the options, so it
stays visible for the user.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_EMAIL, CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import voluptuous as vol

from . import async_get_server, async_release_server
from .cloud import REGIONS, CloudAuthError, CloudDevice, CloudError, async_fetch_devices
from .const import (
    CONF_CALLBACK_IP,
    CONF_CALLBACK_PORT,
    CONF_DEVICE,
    CONF_LANIP_KEY,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .lan import (
    AylaLanDevice,
    InvalidKey,
    ModuleUnreachable,
    NoCallback,
    async_get_host_symname,
    get_local_ip,
)

_LOGGER = logging.getLogger(__name__)

VALIDATE_TIMEOUT = 20
PLAIN_TEXT = TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT))
PORT_SELECTOR = NumberSelector(
    NumberSelectorConfig(min=1024, max=65535, step=1, mode=NumberSelectorMode.BOX)
)
INTERVAL_SELECTOR = NumberSelector(
    NumberSelectorConfig(
        min=10, max=3600, step=1, mode=NumberSelectorMode.BOX, unit_of_measurement="s"
    )
)


def _settings_schema(values: dict[str, Any], *, advanced: bool = True) -> vol.Schema:
    schema: dict[Any, Any] = {
        vol.Required(CONF_HOST, default=values.get(CONF_HOST, "")): PLAIN_TEXT,
        vol.Required(CONF_LANIP_KEY, default=values.get(CONF_LANIP_KEY, "")): PLAIN_TEXT,
        vol.Required(
            CONF_CALLBACK_PORT, default=values.get(CONF_CALLBACK_PORT, DEFAULT_PORT)
        ): PORT_SELECTOR,
        vol.Optional(
            CONF_CALLBACK_IP,
            description={"suggested_value": values.get(CONF_CALLBACK_IP)},
        ): PLAIN_TEXT,
    }
    if advanced:
        schema[
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=values.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            )
        ] = INTERVAL_SELECTOR
    return vol.Schema(schema)


def _clean(user_input: dict[str, Any]) -> dict[str, Any]:
    """Tidy the form: number selectors return floats, copied keys carry spaces."""
    data = dict(user_input)
    data[CONF_HOST] = data[CONF_HOST].strip()
    data[CONF_LANIP_KEY] = data[CONF_LANIP_KEY].strip()
    data[CONF_CALLBACK_PORT] = int(data[CONF_CALLBACK_PORT])
    if CONF_SCAN_INTERVAL in data:
        data[CONF_SCAN_INTERVAL] = int(data[CONF_SCAN_INTERVAL])
    if not (data.get(CONF_CALLBACK_IP) or "").strip():
        data.pop(CONF_CALLBACK_IP, None)
    return data


async def async_validate(hass: HomeAssistant, data: dict[str, Any]) -> tuple[str, str]:
    """Open a short session; returns the serial number and the device name."""
    host = data[CONF_HOST]
    session = async_get_clientsession(hass)
    serial = await async_get_host_symname(session, host)
    server = await async_get_server(hass, data[CONF_CALLBACK_PORT])
    local_ip = data.get(CONF_CALLBACK_IP) or await hass.async_add_executor_job(
        get_local_ip, host
    )
    device = AylaLanDevice(session, server, host, data[CONF_LANIP_KEY], local_ip)
    device.start()
    try:
        result = await device.async_read(["device_name"], VALIDATE_TIMEOUT)
    finally:
        await device.async_stop()
        await async_release_server(hass, server)
    if not device.called_back:
        raise NoCallback
    if not result:
        raise InvalidKey
    return serial, result["device_name"] or serial


class _CloudFetchMixin:
    """The steps that fetch the LAN key from FGLair. The password is not stored."""

    _cloud_devices: dict[str, CloudDevice]
    _prefill: dict[str, Any]

    def _cloud_candidates(self, devices: list[CloudDevice]) -> list[CloudDevice]:
        return devices

    async def _async_cloud_done(self) -> ConfigFlowResult:
        raise NotImplementedError

    async def async_step_cloud(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                devices = await async_fetch_devices(
                    async_get_clientsession(self.hass),
                    user_input[CONF_REGION],
                    user_input[CONF_EMAIL],
                    user_input[CONF_PASSWORD],
                )
            except CloudAuthError:
                errors["base"] = "invalid_auth"
            except CloudError as err:
                _LOGGER.debug("FGLair cloud error: %s", err)
                errors["base"] = "cloud_error"
            else:
                candidates = self._cloud_candidates(devices)
                if candidates:
                    self._cloud_devices = {d.dsn: d for d in candidates}
                    return await self.async_step_cloud_device()
                errors["base"] = "no_devices"

        return self.async_show_form(
            step_id="cloud",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_REGION, default="eu"): SelectSelector(
                        SelectSelectorConfig(
                            options=list(REGIONS),
                            translation_key=CONF_REGION,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(CONF_EMAIL): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.EMAIL)
                    ),
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_cloud_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            device = self._cloud_devices[user_input[CONF_DEVICE]]
            self._prefill[CONF_LANIP_KEY] = device.lanip_key
            if device.lan_ip:
                self._prefill[CONF_HOST] = device.lan_ip
            return await self._async_cloud_done()

        options = [
            SelectOptionDict(value=d.dsn, label=f"{d.name} ({d.lan_ip or d.dsn})")
            for d in self._cloud_devices.values()
        ]
        return self.async_show_form(
            step_id="cloud_device",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE): SelectSelector(
                        SelectSelectorConfig(options=options)
                    )
                }
            ),
        )


class FGLairConfigFlow(_CloudFetchMixin, ConfigFlow, domain=DOMAIN):
    """Add one air conditioner."""

    VERSION = 1

    def __init__(self) -> None:
        self._prefill = {}
        self._cloud_devices = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return FGLairOptionsFlow()

    def _cloud_candidates(self, devices: list[CloudDevice]) -> list[CloudDevice]:
        known = {entry.unique_id for entry in self._async_current_entries()}
        return [device for device in devices if device.dsn not in known]

    async def _async_cloud_done(self) -> ConfigFlowResult:
        return await self.async_step_manual()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(step_id="user", menu_options=["manual", "cloud"])

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            data = _clean(user_input)
            try:
                serial, name = await async_validate(self.hass, data)
            except ModuleUnreachable:
                errors["base"] = "cannot_connect"
            except NoCallback:
                errors["base"] = "no_callback"
            except InvalidKey:
                errors["base"] = "invalid_key"
            except OSError as err:
                _LOGGER.debug("Cannot listen for callbacks: %s", err)
                errors["base"] = "port_in_use"
            else:
                await self.async_set_unique_id(serial)
                self._abort_if_unique_id_configured(updates=data)
                return self.async_create_entry(title=name, data=data)
            self._prefill = data

        return self.async_show_form(
            step_id="manual",
            data_schema=_settings_schema(self._prefill, advanced=False),
            errors=errors,
        )


class FGLairOptionsFlow(_CloudFetchMixin, OptionsFlow):
    """Shows and changes the settings, including the visible LAN key."""

    def __init__(self) -> None:
        self._prefill = {}
        self._cloud_devices = {}

    async def _async_cloud_done(self) -> ConfigFlowResult:
        return await self.async_step_settings()

    def _cloud_candidates(self, devices: list[CloudDevice]) -> list[CloudDevice]:
        return [d for d in devices if d.dsn == self.config_entry.unique_id]

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        self._prefill = dict(self.config_entry.data)
        return self.async_show_menu(step_id="init", menu_options=["settings", "cloud"])

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            # Saving reloads the entry through its update listener.
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=_clean(user_input)
            )
            return self.async_create_entry(title="", data={})
        return self.async_show_form(
            step_id="settings", data_schema=_settings_schema(self._prefill)
        )
