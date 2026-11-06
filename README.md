# FireSense Multi-Zone — Educational MVP

Three-zone sensor dashboard and simulated water-delivery approval workflow. **Not a real fire safety system.**

## Run backend + dashboard

```bash
cd backend
python -m venv .venv
# activate your virtual environment
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

**Before running beyond a private test LAN:** change the demo device/admin keys with environment variables `DEVICE_KEY` and `ADMIN_KEY`. HTTP is unencrypted. Do not expose this prototype to the public internet.

## Test without ESP32

```bash
curl -X POST http://localhost:8000/api/telemetry -H 'Content-Type: application/json' -H 'X-Device-Key: demo-device-key' -d '{"device_id":"ESP32-01","sequence":1,"zones":[{"zone_id":"A","smoke_raw":200,"temperature_c":28},{"zone_id":"B","smoke_raw":600,"temperature_c":46},{"zone_id":"C","smoke_raw":190,"temperature_c":26}],"water":{"flow_lpm":0,"volume_ml":0,"pump_on":false,"active_valve":null}}'
```

For firmware: install ESP32 board support, OneWire and DallasTemperature libraries; update Wi-Fi credentials and backend LAN IP. Firmware only uploads MQ-2 and DS18B20 readings; flow sensing, command polling, and physical actuation are **not implemented**.

See [docs/DATA_FLOW.md](docs/DATA_FLOW.md).
