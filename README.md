# FGLair Local

**English** · [Nederlands](README.nl.md)

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Validate](https://github.com/wilcofoppen/fglair_local/actions/workflows/validate.yml/badge.svg)](https://github.com/wilcofoppen/fglair_local/actions/workflows/validate.yml)

<img src="custom_components/fglair_local/brand/logo@2x.png" alt="FGLair Local" width="360">

Home Assistant integration to control Fujitsu air conditioners with an AC-UTY Wi-Fi module locally, using Ayla LAN mode.

- No cloud needed after setup, no MQTT, no add-on, and no Python packages beyond Home Assistant itself.
- Fully configurable through the UI.
- The LAN key stays visible in the configuration.

> Not affiliated with Fujitsu General or Ayla Networks.

## Installation

**Via HACS:** add `https://github.com/wilcofoppen/fglair_local` as a *custom repository* (category *Integration*), install it, and restart Home Assistant.

**Manually:**

1. Copy the `custom_components/fglair_local` folder to the `config/custom_components` folder of Home Assistant.
2. Restart Home Assistant.

Then go to **Settings > Devices & services > Add integration** and choose **FGLair Local**. Repeat for every air conditioner.

Home Assistant 2026.3 or newer is required for the integration icon.

## Setup

Choose one of two routes:

- **Enter IP address and LAN key:** fill in both yourself.
- **Fetch the LAN key from my FGLair account:** sign in and pick a unit. The IP address and key are filled in for you. Your password is not stored.

You can view or change the LAN key later via **Configure > View or change settings**, where you can also fetch the key again.

## Network

The air conditioner calls back to Home Assistant, by default on TCP port 8888.

- Home Assistant OS works without extra steps.
- With Docker, run the container with `network_mode: host`.
- The unit and Home Assistant must be in the same subnet unless your network is set up for it.
- Close the FGLair app where possible: a module talks to one LAN client at a time.
- Give the units a fixed DHCP reservation.

If a unit stays "unavailable", check the port and firewall first. A message about the key means the LAN key is wrong.

## What you get

| Type | Content | Default |
| --- | --- | --- |
| Climate | Mode, setpoint, fan, vertical swing, eco and boost presets | Enabled |
| Sensors | Indoor and outdoor temperature, error codes, status, firmware | Enabled |
| Switches | Eco, powerful, frost protection, vertical swing | Enabled |
| Select | Vertical louver position | Enabled |
| Other sensors and switches | Timers, presence, model, service values | Disabled, enable per entity |

Features the unit does not have according to `device_capabilities`, such as horizontal swing, do not appear. Properties the unit does not answer get no entity.

Every property stays reachable through the `fglair_local.set_property` action:

```yaml
action: fglair_local.set_property
data:
  device_id: <device-id>
  name: indoor_fan_control
  value: 1
```

## Known limitations

- For the disabled entities, the meaning is inferred from the property name and not confirmed. Test them carefully.
- `test_run` and `reboot_start` are deliberately only exposed as sensors. Writing is possible through the action.
- `child_lock_pin` and the service contact details are never read.
- Port 8888 and the communication with the module use plain HTTP; the messages themselves are encrypted.
- Signing in with your FGLair account uses the same app credentials as the official FGLair app and other open-source projects.

## Contributing

Issues and pull requests are welcome at [github.com/wilcofoppen/fglair_local/issues](https://github.com/wilcofoppen/fglair_local/issues). Please mention your unit model and Home Assistant version.

## License

[MIT](LICENSE)
