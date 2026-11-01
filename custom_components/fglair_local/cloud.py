"""One-time lookup of the LAN key in the FGLair cloud, used only by the config flow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import aiohttp

# Public app identifiers of the FGLair app, per region.
REGIONS = {
    "eu": (
        "user-field-eu.aylanetworks.com",
        "ads-eu.aylanetworks.com",
        "FGLair-eu-id",
        "FGLair-eu-gpFbVBRoiJ8E3QWJ-QRULLL3j3U",
    ),
    "us": (
        "user-field.aylanetworks.com",
        "ads-field.aylanetworks.com",
        "CJIOSP-id",
        "CJIOSP-Vb8MQL_lFiYQ7DKjN0eCFXznKZE",
    ),
    "cn": (
        "user-field.ayla.com.cn",
        "ads-field.ayla.com.cn",
        "FGLairField-cn-id",
        "FGLairField-cn-zezg7Y60YpAvy3HPwxvWLnd4Oh4",
    ),
}
TIMEOUT = aiohttp.ClientTimeout(total=20)


class CloudAuthError(Exception):
    """The FGLair login was refused."""


class CloudError(Exception):
    """The FGLair cloud could not be reached."""


@dataclass
class CloudDevice:
    dsn: str
    name: str
    lan_ip: str | None
    lanip_key: str


async def _get(session: aiohttp.ClientSession, url: str, token: str) -> Any:
    async with session.get(
        url, headers={"Authorization": f"auth_token {token}"}, timeout=TIMEOUT
    ) as resp:
        resp.raise_for_status()
        return await resp.json(content_type=None)


async def async_fetch_devices(
    session: aiohttp.ClientSession, region: str, email: str, password: str
) -> list[CloudDevice]:
    """Log in and return every device in the account, with its LAN key."""
    user_server, device_server, app_id, app_secret = REGIONS[region]
    try:
        async with session.post(
            f"https://{user_server}/users/sign_in.json",
            json={
                "user": {
                    "email": email,
                    "password": password,
                    "application": {"app_id": app_id, "app_secret": app_secret},
                }
            },
            timeout=TIMEOUT,
        ) as resp:
            if resp.status in (401, 403):
                raise CloudAuthError
            resp.raise_for_status()
            token = (await resp.json(content_type=None))["access_token"]

        devices = []
        listing = await _get(session, f"https://{device_server}/apiv1/devices.json", token)
        for entry in listing:
            device = entry["device"]
            dsn = device["dsn"]
            lan = await _get(session, f"https://{device_server}/apiv1/dsns/{dsn}/lan.json", token)
            devices.append(
                CloudDevice(
                    dsn=dsn,
                    name=device.get("product_name") or dsn,
                    lan_ip=device.get("lan_ip"),
                    lanip_key=lan["lanip"]["lanip_key"],
                )
            )
    except (aiohttp.ClientError, TimeoutError, KeyError, ValueError) as err:
        raise CloudError(str(err)) from err
    return devices
