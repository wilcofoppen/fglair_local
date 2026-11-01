"""Ayla LAN-mode client for FGLair modules.

The module is the HTTP client: we register with it, it calls back to a small
server of ours, performs a key exchange and then fetches commands one by one.
This file has no Home Assistant imports, so it can be tested on its own.
"""

from __future__ import annotations

import asyncio
import base64
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import hmac
import json
import logging
import math
import random
import socket
import string
import time
from typing import Any

import aiohttp
from aiohttp import web
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

_LOGGER = logging.getLogger(__name__)

HEARTBEAT_INTERVAL = 10
SESSION_TIMEOUT = 30
REQUEST_TIMEOUT = 5
READ_BACK_DELAY = 3
BLOCK_SIZE = 16


class AylaLanError(Exception):
    """Base error for LAN communication."""


class ModuleUnreachable(AylaLanError):
    """The module does not answer on port 80."""


class NoCallback(AylaLanError):
    """The module accepted the registration but never called back."""


class InvalidKey(AylaLanError):
    """The module called back but cannot read our encrypted commands."""


def _digest(key: bytes, msg: bytes) -> bytes:
    return hmac.digest(key, msg, hashlib.sha256)


def _build_key(key: bytes, msg: bytes) -> bytes:
    return _digest(key, _digest(key, msg) + msg)


class _Channel:
    """Keys for one direction. The CBC chain continues across messages."""

    def __init__(self, lanip_key: bytes, msg: bytes) -> None:
        self.sign_key = _build_key(lanip_key, msg + b"0")
        cipher = Cipher(
            algorithms.AES(_build_key(lanip_key, msg + b"1")),
            modes.CBC(_build_key(lanip_key, msg + b"2")[:BLOCK_SIZE]),
        )
        self.encryptor = cipher.encryptor()
        self.decryptor = cipher.decryptor()


@dataclass
class _Write:
    name: str
    value: Any
    base_type: str


async def async_get_host_symname(session: aiohttp.ClientSession, host: str) -> str:
    """Return the module's serial number, without any key."""
    try:
        async with session.get(
            f"http://{host}/regtoken.json",
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
        ) as resp:
            data = json.loads(await resp.text())
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        raise ModuleUnreachable(str(err)) from err
    try:
        return data["host_symname"]
    except KeyError as err:
        raise ModuleUnreachable("no host_symname in regtoken.json") from err


def get_local_ip(target: str) -> str:
    """Return the local address that routes to target. Blocking but instant."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect((target, 80))
        return sock.getsockname()[0]


class AylaLanServer:
    """The callback server. One port serves every module, told apart by IP."""

    def __init__(self, port: int) -> None:
        self.port = port
        self._devices: dict[str, AylaLanDevice] = {}
        self._runner: web.AppRunner | None = None

    @property
    def idle(self) -> bool:
        return not self._devices

    async def async_start(self) -> None:
        app = web.Application()
        app.router.add_route("*", "/local_lan/{tail:.*}", self._handle)
        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        site = web.TCPSite(runner, port=self.port)
        try:
            await site.start()
        except OSError:
            await runner.cleanup()
            raise
        self._runner = runner

    async def async_stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()
            self._runner = None

    def add(self, device: AylaLanDevice) -> None:
        self._devices[device.host] = device

    def remove(self, device: AylaLanDevice) -> None:
        if self._devices.get(device.host) is device:
            del self._devices[device.host]

    async def _handle(self, request: web.Request) -> web.Response:
        device = self._devices.get(request.remote or "")
        if device is None:
            return web.Response(status=404)
        tail = request.match_info["tail"]
        try:
            if tail == "key_exchange.json" and request.method == "POST":
                body = await request.json(loads=json.loads)
                return web.json_response(device.handle_key_exchange(body["key_exchange"]))
            if tail == "commands.json" and request.method == "GET":
                payload, more = device.handle_command_request()
                return web.json_response(payload, status=206 if more else 200)
            if "datapoint" in tail and request.method == "POST":
                device.handle_datapoint(await request.read(), request.query)
                return web.Response()
        except (KeyError, TypeError, ValueError) as err:
            _LOGGER.debug("%s: bad request on %s: %r", device.host, tail, err)
            return web.Response(status=400)
        return web.Response(status=404)


class AylaLanDevice:
    """One module: session keys, command queue and the latest values."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        server: AylaLanServer,
        host: str,
        lanip_key: str,
        local_ip: str,
    ) -> None:
        self.host = host
        self.values: dict[str, Any] = {}
        self.key_id: int | None = None
        self.unreadable: set[str] = set()
        self._session = session
        self._server = server
        self._lanip_key = lanip_key.encode()
        self._local_ip = local_ip
        self._app: _Channel | None = None
        self._dev: _Channel | None = None
        self._seq_no = 0
        self._cmd_id = 0
        self._writes: deque[_Write] = deque()
        self._reads: deque[str] = deque()
        self._cmd_names: dict[int, str] = {}
        self._waiting: set[str] = set()
        self._reads_done = asyncio.Event()
        self._wake = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._last_contact = 0.0
        self._registered = False
        self._listeners: list[Callable[[], None]] = []

    @property
    def connected(self) -> bool:
        return time.monotonic() - self._last_contact < SESSION_TIMEOUT

    @property
    def called_back(self) -> bool:
        """True once a key exchange took place."""
        return self._app is not None

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def start(self) -> None:
        self._server.add(self)
        self._task = asyncio.create_task(self._heartbeat_loop())

    async def async_stop(self) -> None:
        self._server.remove(self)
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    def queue_write(self, name: str, value: Any, base_type: str) -> None:
        """Queue a write. A newer write replaces a queued one, and writes go first."""
        for write in self._writes:
            if write.name == name:
                write.value, write.base_type = value, base_type
                break
        else:
            self._writes.append(_Write(name, value, base_type))
        self.values[name] = value
        self._notify_listeners()
        self._wake.set()
        # Modules do not reliably echo a write, so read it back.
        asyncio.get_running_loop().call_later(READ_BACK_DELAY, self.queue_reads, [name])

    def queue_reads(self, names: list[str]) -> None:
        queued = set(self._reads)
        self._reads.extend(n for n in names if n not in queued)
        self._wake.set()

    async def async_read(self, names: list[str], timeout: float) -> dict[str, Any]:
        """Read properties and wait for the answers; returns what came in."""
        self._waiting.update(names)
        self._reads_done.clear()
        self.queue_reads(names)
        try:
            await asyncio.wait_for(self._reads_done.wait(), timeout)
        except TimeoutError:
            _LOGGER.debug("%s: no answer for %s", self.host, sorted(self._waiting))
        self._waiting.difference_update(names)
        return {n: self.values[n] for n in names if n in self.values}

    def handle_key_exchange(self, key: dict[str, Any]) -> dict[str, Any]:
        if key["ver"] != 1 or key["proto"] != 1 or key.get("sec"):
            raise ValueError(f"unsupported key exchange: {key}")
        random_2 = "".join(random.choices(string.ascii_letters + string.digits, k=16))
        time_2 = time.monotonic_ns() % 2**40
        r_1, t_1 = key["random_1"].encode(), str(key["time_1"]).encode()
        r_2, t_2 = random_2.encode(), str(time_2).encode()
        self._app = _Channel(self._lanip_key, r_1 + r_2 + t_1 + t_2)
        self._dev = _Channel(self._lanip_key, r_2 + r_1 + t_2 + t_1)
        self.key_id = key["key_id"]
        self._seq_no = 0
        self._touch()
        return {"random_2": random_2, "time_2": time_2}

    def handle_command_request(self) -> tuple[dict[str, str], bool]:
        if self._app is None:
            raise ValueError("no session")
        self._touch()
        data: dict[str, Any] = {}
        if self._writes:
            write = self._writes.popleft()
            prop_id = "".join(random.choices(string.ascii_letters + string.digits, k=8))
            data = {
                "properties": [
                    {
                        "property": {
                            "base_type": write.base_type,
                            "name": write.name,
                            "value": write.value,
                            "id": prop_id,
                        }
                    }
                ]
            }
        elif self._reads:
            name = self._reads.popleft()
            self._cmd_id += 1
            self._cmd_names[self._cmd_id] = name
            data = {
                "cmds": [
                    {
                        "cmd": {
                            "method": "GET",
                            "resource": f"property.json?name={name}",
                            "uri": "/local_lan/property/datapoint.json",
                            "data": "",
                            "cmd_id": self._cmd_id,
                        }
                    }
                ]
            }
        text = json.dumps({"seq_no": self._seq_no, "data": data}).encode()
        self._seq_no += 1
        size = math.ceil(len(text) / BLOCK_SIZE) * BLOCK_SIZE
        payload = {
            "enc": base64.b64encode(
                self._app.encryptor.update(text.ljust(size, b"\0"))
            ).decode(),
            "sign": base64.b64encode(_digest(self._app.sign_key, text)).decode(),
        }
        return payload, bool(self._writes or self._reads)

    def handle_datapoint(self, raw: bytes, query: Any) -> None:
        if self._dev is None:
            raise ValueError("no session")
        self._touch()
        # Mark the read as answered first: some properties return unparsable data.
        name = self._cmd_names.pop(int(query.get("cmd_id", -1)), None)
        try:
            self._apply_datapoint(raw)
        except ValueError:
            if name:
                self.unreadable.add(name)
            raise
        finally:
            if name:
                self._read_answered(name)

    def _apply_datapoint(self, raw: bytes) -> None:
        body = json.loads(raw)
        text = self._dev.decryptor.update(base64.b64decode(body["enc"])).rstrip(b"\0")
        sign = base64.b64encode(_digest(self._dev.sign_key, text)).decode()
        if sign != body["sign"]:
            raise ValueError("invalid signature")
        data = json.loads(text).get("data") or {}
        if "name" not in data:
            return
        self.values[data["name"]] = data.get("value")
        self.unreadable.discard(data["name"])
        self._read_answered(data["name"])
        self._notify_listeners()

    def _read_answered(self, name: str) -> None:
        self._waiting.discard(name)
        if not self._waiting:
            self._reads_done.set()

    def _touch(self) -> None:
        self._last_contact = time.monotonic()

    def _notify_listeners(self) -> None:
        for listener in list(self._listeners):
            listener()

    async def _register(self) -> None:
        pending = bool(self._writes or self._reads)
        body = {
            "local_reg": {
                "ip": self._local_ip,
                "notify": int(pending),
                "port": self._server.port,
                "uri": "/local_lan",
            }
        }
        method = "PUT" if self._registered and self.connected else "POST"
        try:
            async with self._session.request(
                method,
                f"http://{self.host}/local_reg.json",
                json=body,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as resp:
                self._registered = resp.status == 202
                if not self._registered:
                    _LOGGER.debug("%s: local_reg returned %s", self.host, resp.status)
        except (aiohttp.ClientError, TimeoutError) as err:
            self._registered = False
            _LOGGER.debug("%s: local_reg failed: %r", self.host, err)

    async def _heartbeat_loop(self) -> None:
        while True:
            self._wake.clear()
            await self._register()
            try:
                await asyncio.wait_for(self._wake.wait(), HEARTBEAT_INTERVAL)
            except TimeoutError:
                pass
