"""FGLair Local: control Fujitsu air conditioners over the LAN, without the cloud."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_DEVICE_ID, CONF_HOST, CONF_NAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from .const import (
    CONF_CALLBACK_IP,
    CONF_CALLBACK_PORT,
    CONF_LANIP_KEY,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PROPERTY_TYPES,
    READ_ONLY,
)
from .coordinator import FGLairCoordinator
from .lan import AylaLanDevice, AylaLanServer, get_local_ip

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

ATTR_VALUE = "value"
SERVICE_SET_PROPERTY = "set_property"
SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_NAME): vol.In(sorted(PROPERTY_TYPES)),
        vol.Required(ATTR_VALUE): vol.Any(cv.boolean, vol.Coerce(int), cv.string),
    }
)

FGLairConfigEntry = ConfigEntry[FGLairCoordinator]


async def async_get_server(hass: HomeAssistant, port: int) -> AylaLanServer:
    """Return the callback server for a port, starting it when needed."""
    servers: dict[int, AylaLanServer] = hass.data.setdefault(DOMAIN, {})
    if port not in servers:
        server = AylaLanServer(port)
        await server.async_start()
        servers[port] = server
    return servers[port]


async def async_release_server(hass: HomeAssistant, server: AylaLanServer) -> None:
    """Stop a callback server once no device uses it."""
    if server.idle:
        hass.data[DOMAIN].pop(server.port, None)
        await server.async_stop()


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the service for properties without an entity."""

    async def async_set_property(call: ServiceCall) -> None:
        name = call.data[CONF_NAME]
        if name in READ_ONLY:
            raise ServiceValidationError(f"{name} is read-only")
        coordinator = _coordinator_for_device(hass, call.data[CONF_DEVICE_ID])
        coordinator.write(name, _cast(name, call.data[ATTR_VALUE]))

    hass.services.async_register(
        DOMAIN, SERVICE_SET_PROPERTY, async_set_property, schema=SERVICE_SCHEMA
    )
    return True


def _cast(name: str, value: Any) -> Any:
    if PROPERTY_TYPES[name] == "string":
        return str(value)
    return int(value)


def _coordinator_for_device(hass: HomeAssistant, device_id: str) -> FGLairCoordinator:
    device = dr.async_get(hass).async_get(device_id)
    for entry in hass.config_entries.async_entries(DOMAIN):
        if (
            device
            and (DOMAIN, entry.unique_id) in device.identifiers
            and entry.state is ConfigEntryState.LOADED
        ):
            return entry.runtime_data
    raise ServiceValidationError(f"No FGLair Local device with id {device_id}")


async def async_setup_entry(hass: HomeAssistant, entry: FGLairConfigEntry) -> bool:
    """Connect to one air conditioner."""
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_CALLBACK_PORT, DEFAULT_PORT)
    try:
        server = await async_get_server(hass, port)
    except OSError as err:
        raise ConfigEntryNotReady(f"Cannot listen on port {port}: {err}") from err

    local_ip = entry.data.get(CONF_CALLBACK_IP) or await hass.async_add_executor_job(
        get_local_ip, host
    )
    device = AylaLanDevice(
        async_get_clientsession(hass), server, host, entry.data[CONF_LANIP_KEY], local_ip
    )
    device.start()
    coordinator = FGLairCoordinator(
        hass, entry, device, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        coordinator.async_shutdown_listener()
        await device.async_stop()
        await async_release_server(hass, server)
        raise

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: FGLairConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: FGLairConfigEntry) -> bool:
    """Disconnect from one air conditioner."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        coordinator = entry.runtime_data
        coordinator.async_shutdown_listener()
        await coordinator.device.async_stop()
        port = entry.data.get(CONF_CALLBACK_PORT, DEFAULT_PORT)
        server = hass.data[DOMAIN].get(port)
        if server:
            await async_release_server(hass, server)
    return unloaded
