# IOTAVX AVX1 – RS-232 Befehlsreferenz

Seriell-Parameter: **9600 Baud / 8 Datenbits / Keine Parität / 1 Stoppbit**

Jeder Befehl wird mit `\r` (Carriage Return) terminiert.

## Power

| Funktion | Befehl | Beschreibung |
|----------|--------|--------------|
| Power On | `@112` | Gerät einschalten |
| Power Off | `@113` | Gerät ausschalten (Standby) |

## Quellenwahl

| Funktion | Befehl | Beschreibung |
|----------|--------|--------------|
| TV (ARC) | `@11B` | HDMI ARC Eingang |
| HDMI 1 | `@116` | HDMI 1 (4K UHD HDR) |
| HDMI 2 | `@115` | HDMI 2 (4K UHD HDR) |
| HDMI 3 | `@15A` | HDMI 3 (4K UHD HDR) |
| HDMI 4 | `@15B` | HDMI 4 |
| HDMI 5 | `@15C` | HDMI 5 |
| HDMI 6 | `@15D` | HDMI 6 |
| Coax | `@117` | S/PDIF koaxial |
| Optical | `@15E` | S/PDIF optisch |
| Analog 1 | `@15F` | Cinch Analog 1 |
| Analog 2 | `@15G` | Cinch Analog 2 |
| Bluetooth | `@15H` | Bluetooth (benötigt IOTAVX BT-Dongle) |
| Source Down | `@15X` | Vorherige Quelle |
| Source Up | `@15Y` | Nächste Quelle |

## Sound-Modi

| Funktion | Befehl | Hinweis |
|----------|--------|---------|
| Mode Up | `@11D` | Nur in Analog 1 & 2 |
| Mode Down | `@13W` | Nur in Analog 1 & 2 |
| Stereo | `@11E` | |
| Pro Logic IIx | `@11F` | |
| All Channel Stereo | `@11C` | |
| Neo:6 | `@13H` | |
| Source Direct | `@13J` | |

## Lautstärke

| Funktion | Befehl | Format |
|----------|--------|--------|
| Volume Set | `@11P` + 3 Zeichen | z.B. `@11P050` für 50% |
| Volume Up | `@11S` | +1 Schritt |
| Volume Down | `@11T` | -1 Schritt |
| Mute On | `@11Q` | |
| Mute Off | `@11R` | |

## Kanal-Trim

| Funktion | Befehl | Beschreibung |
|----------|--------|--------------|
| Surround/Back Up | `@11g` | +1 Schritt |
| Surround/Back Down | `@11j` | -1 Schritt |
| Center Up | `@11k` | +1 Schritt |
| Center Down | `@11n` | -1 Schritt |
| Sub Up | `@11p` | +1 Schritt |
| Sub Down | `@11r` | -1 Schritt |

## Display & System

| Funktion | Befehl | Format |
|----------|--------|--------|
| Dimmer | `@12D` + 2 Zeichen | `00` = aus, `10` = voll, z.B. `@12D05` |
| System Reset | `@12L` | Werkseinstellungen laden |
| Status abfragen | `@12S` | Gibt Gerätestatus zurück |

## OSD-Menü Navigation

| Funktion | Befehl |
|----------|--------|
| Menü öffnen | `@141` |
| Pfeil hoch | `@142` |
| Pfeil runter | `@143` |
| Pfeil rechts | `@144` |
| Pfeil links | `@145` |
| Enter/OK | `@146` |
| Exit | `@147` |
| Zurück | `@148` |
