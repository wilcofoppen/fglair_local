# FGLair Local

[English](README.md) · **Nederlands**

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz) [![Validate](https://github.com/wilcofoppen/fglair_local/actions/workflows/validate.yml/badge.svg)](https://github.com/wilcofoppen/fglair_local/actions/workflows/validate.yml)

Home Assistant-integratie om Fujitsu-airco's met een AC-UTY-wifimodule lokaal te bedienen, via Ayla LAN-modus.

- Geen cloud nodig na het instellen, geen MQTT, geen add-on en geen Python-pakketten buiten Home Assistant.
- Volledig via de GUI in te stellen.
- De LAN-sleutel blijft zichtbaar in de configuratie.

## Installeren

**Via HACS:** voeg `https://github.com/wilcofoppen/fglair_local` toe als *custom repository* (categorie *Integration*), installeer en herstart Home Assistant.

**Handmatig:**

1. Kopieer de map `custom_components/fglair_local` naar de `config/custom_components`-map van Home Assistant.
2. Herstart Home Assistant.
3. Ga naar **Instellingen > Apparaten en diensten > Integratie toevoegen** en kies **FGLair Local**.
4. Herhaal stap 3 voor elke airco.

## Instellen

Kies een van de twee routes:

- **IP-adres en LAN-sleutel invoeren:** vul beide zelf in.
- **LAN-sleutel ophalen uit mijn FGLair-account:** log in en kies een airco. IP-adres en sleutel worden ingevuld. Je wachtwoord wordt niet opgeslagen.

De LAN-sleutel bekijken of wijzigen doe je later via **Configureren > Instellingen bekijken of wijzigen**. Daar kun je de sleutel ook opnieuw ophalen.

## Netwerk

De airco belt terug naar Home Assistant, standaard op TCP-poort 8888.

- Home Assistant OS werkt zonder extra stappen.
- Gebruik je Docker, draai de container dan met `network_mode: host`.
- De airco en Home Assistant moeten in hetzelfde subnet zitten, tenzij je het netwerk daarop hebt ingericht.
- Sluit de FGLair-app zoveel mogelijk, want een module praat met één LAN-client tegelijk.
- Geef de airco's een vaste DHCP-reservering.

Blijft een airco op "niet beschikbaar" staan, controleer dan eerst de poort en de firewall. Bij de melding over de sleutel klopt de LAN-sleutel niet.

## Wat je krijgt

| Type | Inhoud | Standaard |
| --- | --- | --- |
| Climate | Stand, setpoint, ventilator, verticale swing, presets eco en boost | Aan |
| Sensoren | Binnen- en buitentemperatuur, foutcodes, status, firmware | Aan |
| Schakelaars | Eco, powerful, vorstbeveiliging, verticale swing | Aan |
| Select | Stand van de verticale lamel | Aan |
| Overige sensoren en schakelaars | Timers, aanwezigheid, model, servicewaarden | Uit, in te schakelen per entiteit |

Functies die de unit volgens `device_capabilities` niet heeft, zoals horizontale swing, verschijnen niet. Properties die de unit niet beantwoordt, krijgen geen entiteit.

Elke property blijft bereikbaar via de actie `fglair_local.set_property`:

```yaml
action: fglair_local.set_property
data:
  device_id: <apparaat-id>
  name: indoor_fan_control
  value: 1
```

## Bekende beperkingen

- Van de uitgeschakelde entiteiten is de betekenis afgeleid van de propertynaam en niet bevestigd. Test ze rustig.
- `test_run` en `reboot_start` zijn bewust alleen zichtbaar als sensor. Schrijven kan via de actie.
- `child_lock_pin` en de servicecontactgegevens worden nooit gelezen.
- De poort 8888 en de communicatie met de module gaan over onversleuteld HTTP; de berichten zelf zijn versleuteld.

Niet verbonden met Fujitsu General of Ayla Networks.
