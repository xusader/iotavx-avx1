# IOTAVX AVX1 – Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue)](https://www.home-assistant.io/)
[![Validate](https://github.com/xusader/iotavx-avx1/actions/workflows/validate.yml/badge.svg)](https://github.com/xusader/iotavx-avx1/actions)

A Home Assistant custom integration for the **IOTAVX AVX1** AV processor, controlled via its **RS-232 serial interface**.

## Features

- **Power** on / off / standby detection
- **Source selection** – all 12 inputs (HDMI 1–6, TV ARC, Coax, Optical, Analog 1/2, Bluetooth)
- **Volume** control (absolute set, step up/down, mute)
- **Sound mode** selection (Stereo, Pro Logic IIx, All Channel Stereo, Neo:6, Source Direct)
- **Surround / Center / Sub trim** adjustments
- **Display dimmer** (0–10)
- **OSD remote control** – menu navigation via `remote` entity
- **Quick-action buttons** – Source Up/Down, Mode Up/Down, Menu, System Reset
- **Status polling** for real-time state updates
- **Automatic reconnection** with exponential backoff
- **Diagnostics** – downloadable debug data for issue reports
- **Config Flow** – UI-based setup
- **HACS compatible**

## Requirements

- Home Assistant **2024.1** or newer
- IOTAVX AVX1 connected via RS-232 serial cable
- A USB-to-serial adapter (e.g. FTDI-based) on the HA host, **or** a network serial bridge (e.g. ser2net, USR-TCP232)

## Installation

### HACS (recommended)

1. Open HACS → **Integrations** → ⋮ menu → **Custom repositories**
2. Add `https://github.com/xusader/iotavx-avx1` as type **Integration**
3. Search for **IOTAVX AVX1** and install
4. Restart Home Assistant

### Manual

1. Copy the `custom_components/iotavx_avx1` folder into your `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **IOTAVX AVX1**
3. Enter the serial port path (e.g. `/dev/ttyUSB0`) or a `socket://host:port` URL for network bridges
4. Done – entities are created automatically

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| `media_player.iotavx_avx1` | Media Player | Main control: power, volume, source, sound mode |
| `remote.iotavx_avx1_remote` | Remote | OSD menu navigation (up/down/left/right/enter/exit/menu) |
| `number.iotavx_avx1_dimmer` | Number | Display brightness (0–10) |
| `number.iotavx_avx1_center_trim` | Number | Center channel trim |
| `number.iotavx_avx1_sub_trim` | Number | Subwoofer trim |
| `number.iotavx_avx1_surround_trim` | Number | Surround / surround back trim |
| `button.iotavx_avx1_menu` | Button | Open OSD menu |
| `button.iotavx_avx1_source_up` | Button | Next source |
| `button.iotavx_avx1_source_down` | Button | Previous source |
| `button.iotavx_avx1_mode_up` | Button | Next sound mode |
| `button.iotavx_avx1_mode_down` | Button | Previous sound mode |
| `button.iotavx_avx1_system_reset` | Button | Factory reset (config category) |

## RS-232 Connection

The AVX1 uses a standard DB9 serial connection:

| Parameter | Value |
|-----------|-------|
| Baud rate | 9600 |
| Data bits | 8 |
| Parity | None |
| Stop bits | 1 |

## Services

### `iotavx_avx1.send_command`

Send a raw RS-232 command to the AVX1.

```yaml
service: iotavx_avx1.send_command
data:
  command: "@112"
```

### `iotavx_avx1.set_dimmer`

Set display dimmer level (0–10).

```yaml
service: iotavx_avx1.set_dimmer
data:
  level: 5
```

### `remote.send_command`

Navigate the OSD menu.

```yaml
service: remote.send_command
target:
  entity_id: remote.iotavx_avx1_remote
data:
  command:
    - menu
    - down
    - down
    - enter
```

Available buttons: `menu`, `up`, `down`, `left`, `right`, `enter`, `exit`, `back`, `return`, `power_on`, `power_off`. You can also send raw RS-232 commands prefixed with `@`.

## Examples

See the `examples/` directory for:

- **`automations.yaml`** – Kino-Modus, Nachtmodus, PS5-Auto-Input, Lautstärke-Begrenzung, OSD-Navigation
- **`lovelace.yaml`** – Full dashboard card with source buttons, sound mode buttons, trim sliders, and OSD navigation grid

## Diagnostics

Go to **Settings → Devices & Services → IOTAVX AVX1 → ⋮ → Download Diagnostics** to generate a debug report including connection state, last device status, and the 50 most recent RS-232 commands with responses.

## Network Serial Bridges

If your HA host is not physically near the AVX1, you can use a network serial bridge:

**ser2net** on a Raspberry Pi near the AVX1:
```
connection: &avx1
  accepter: tcp,2217
  connector: serialdev,/dev/ttyUSB0,9600n81,local
```

Then configure the integration with: `socket://192.168.1.x:2217`

## Troubleshooting

- **"Could not connect"** – Check that the serial port exists (`ls /dev/ttyUSB*`) and that the HA user has permission (`sudo usermod -aG dialout homeassistant`)
- **No status updates** – The status parser is firmware-dependent. Enable debug logging and share the raw `@12S` response to improve parsing
- **Commands not working** – Ensure the RS-232 cable is a straight-through cable (not null-modem)

Enable debug logging:
```yaml
logger:
  default: warning
  logs:
    custom_components.iotavx_avx1: debug
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a Pull Request

## License

MIT License – see [LICENSE](LICENSE).
