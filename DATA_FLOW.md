# FireSense MVP — Data flow & interfaces

**Purpose:** educational prototype, NOT a certified fire alarm or extinguishing system. No real suppression control is implemented.

1. MQ-2 modules -> ESP32 ADC1: raw 0–4095 (not ppm, not calibrated smoke concentration). Modules may output 5V: level shift before connecting ESP32.
2. DS18B20 -> ESP32 1-Wire: degrees Celsius. Use pull-up resistors; check disconnect sentinel -127C.
3. Flow sensor -> ESP32 pulse GPIO (future): L/min and cumulative mL after calibration; ensure signal level compatible with 3.3V.
4. ESP32 -> POST `/api/telemetry` every ~2 s with device key; server timestamps receipt and writes SQLite `readings` and `water`.
5. Backend -> GET `/api/state` for Dashboard every ~2 s; anomaly events are DEMO thresholds only.
6. Dashboard -> POST `/api/demo/approve` with admin key, zone A/B/C, target 100–1000 mL. Backend stores short-lived command.
7. ESP32 -> GET `/api/device/command?device_id=ESP32-01` (API provided, firmware does NOT yet poll or actuate); command must be validated locally and never used for real suppression.
8. ESP32 -> POST `/api/device/ack` to report completed/rejected/stopped (API provided, firmware not implemented).

## Example payload
```json
{"device_id":"ESP32-01","sequence":1,"zones":[{"zone_id":"A","smoke_raw":200,"temperature_c":28},{"zone_id":"B","smoke_raw":600,"temperature_c":44},{"zone_id":"C","smoke_raw":190,"temperature_c":26}],"water":{"flow_lpm":0,"volume_ml":0,"pump_on":false,"active_valve":null}}
```

## Data ownership
- ESP32 measures and reports; no internet required if local LAN.
- Backend receives, validates, timestamps, persists, and manages DEMO commands.
- Dashboard displays, does not directly control GPIO.
- GitHub stores source code, not running sensor telemetry or the SQLite database.

## Safety and production gaps
- Do not deploy as life-safety equipment. No real fire tests or chemical agents.
- Demo command endpoint is only a proof of workflow, not a secure production authorization system. Use HTTPS, user authentication, role permissions, audit trails, rate limiting and secure device identities before any real deployment.
- Physical emergency stop, independent pump timeouts, dry-run protection, flow failure handling, check valves, pressure compatibility and power protection required before connecting a low-pressure demo pump.
- MQTT/FCM optional later. Dashboard polling is not mobile push notification.
- With one flow sensor on the common line, measured flow is aggregate; ensure only one valve is active for zone attribution.
