# Changelog

## [1.0.0] – 2026-03-22

### Added
- Initial release
- **Media Player** entity: power, volume (set/step/mute), source selection (12 inputs), sound mode selection (5 modes)
- **Remote** entity: OSD menu navigation with 12 button commands + raw RS-232 passthrough
- **Number** entities: display dimmer (0–10), center/sub/surround trim
- **Button** entities: menu, source up/down, mode up/down, system reset
- **Sensor** entities: connection status (diagnostic), current source, current sound mode
- **Switch** entity: mute toggle
- **Services**: `send_command`, `set_dimmer`, `navigate_menu`
- **DataUpdateCoordinator** for centralised polling
- **Config Flow** with serial port detection
- **Options Flow** for configurable polling interval (5–120s)
- **Diagnostics** support for debug data export
- **Automatic reconnection** with exponential backoff (3 attempts)
- **Command logging** (last 50 commands stored for diagnostics)
- **Network serial bridge** support via `socket://host:port`
- **HACS** compatible with GitHub Actions CI validation
- **Translations**: German (de), English (en)
- **Example automations** and **Lovelace dashboard** card
- **RS-232 command reference** documentation
