import json, os, sqlite3, time, uuid
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

DB = os.getenv('DB_PATH','firesense.db')
DEVICE_KEY = os.getenv('DEVICE_KEY','demo-device-key')
ADMIN_KEY = os.getenv('ADMIN_KEY','demo-admin-key')
app = FastAPI(title='FireSense MVP Demo API')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:8000','http://127.0.0.1:8000'], allow_methods=['*'], allow_headers=['*'])

@contextmanager
def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()

@app.on_event('startup')
def setup():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS readings (id INTEGER PRIMARY KEY, received_at REAL, device_id TEXT, sequence INTEGER, zone_id TEXT, smoke_raw INTEGER, temperature_c REAL);
        CREATE TABLE IF NOT EXISTS water (id INTEGER PRIMARY KEY, received_at REAL, device_id TEXT, flow_lpm REAL, volume_ml REAL, pump_on INTEGER, active_valve TEXT);
        CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, created_at REAL, zone_id TEXT, kind TEXT, detail TEXT);
        CREATE TABLE IF NOT EXISTS commands (id TEXT PRIMARY KEY, created_at REAL, expires_at REAL, device_id TEXT, zone_id TEXT, target_ml INTEGER, status TEXT);
        ''')

class Zone(BaseModel):
    zone_id: str
    smoke_raw: int = Field(ge=0, le=4095)
    temperature_c: float = Field(ge=-55, le=125)
class Water(BaseModel):
    flow_lpm: float = Field(ge=0)
    volume_ml: float = Field(ge=0)
    pump_on: bool
    active_valve: Optional[str] = None
class Telemetry(BaseModel):
    device_id: str
    sequence: int = Field(ge=0)
    zones: list[Zone]
    water: Water
class Approval(BaseModel):
    device_id: str = 'ESP32-01'
    zone_id: str
    target_ml: int = Field(ge=100, le=1000)

def require_key(value, expected):
    if value != expected: raise HTTPException(401,'Invalid key')

@app.post('/api/telemetry')
def telemetry(data: Telemetry, x_device_key: str = Header(default='')):
    require_key(x_device_key, DEVICE_KEY)
    now = time.time()
    with db() as c:
        for z in data.zones:
            if z.zone_id not in ('A','B','C'): raise HTTPException(422,'Invalid zone')
            c.execute('INSERT INTO readings(received_at,device_id,sequence,zone_id,smoke_raw,temperature_c) VALUES(?,?,?,?,?,?)', (now,data.device_id,data.sequence,z.zone_id,z.smoke_raw,z.temperature_c))
            # Illustrative monitoring thresholds only; not a fire alarm or suppression trigger.
            if z.temperature_c > 45 or z.temperature_c < 10 or z.smoke_raw > 2500:
                c.execute('INSERT INTO events VALUES(?,?,?,?,?)',(str(uuid.uuid4()),now,z.zone_id,'DEMO_ANOMALY',f'T={z.temperature_c}C, raw={z.smoke_raw}'))
        w = data.water
        c.execute('INSERT INTO water(received_at,device_id,flow_lpm,volume_ml,pump_on,active_valve) VALUES(?,?,?,?,?,?)',(now,data.device_id,w.flow_lpm,w.volume_ml,int(w.pump_on),w.active_valve))
    return {'ok':True, 'server_time':now}

@app.get('/api/state')
def state():
    with db() as c:
        zones = {}
        for zid in ('A','B','C'):
            row = c.execute('SELECT * FROM readings WHERE zone_id=? ORDER BY id DESC LIMIT 1',(zid,)).fetchone()
            zones[zid] = dict(row) if row else None
        water = c.execute('SELECT * FROM water ORDER BY id DESC LIMIT 1').fetchone()
        events = [dict(r) for r in c.execute('SELECT * FROM events ORDER BY created_at DESC LIMIT 15')]
        commands = [dict(r) for r in c.execute('SELECT * FROM commands ORDER BY created_at DESC LIMIT 10')]
    return {'zones':zones,'water':dict(water) if water else None,'events':events,'commands':commands}

@app.post('/api/demo/approve')
def approve(data: Approval, x_admin_key: str = Header(default='')):
    require_key(x_admin_key, ADMIN_KEY)
    if data.zone_id not in ('A','B','C'): raise HTTPException(422,'Invalid zone')
    now=time.time(); cid=str(uuid.uuid4())
    with db() as c:
        c.execute('INSERT INTO commands VALUES(?,?,?,?,?,?,?)',(cid,now,now+15,data.device_id,data.zone_id,data.target_ml,'pending'))
    return {'command_id':cid,'status':'pending','expires_in_seconds':15}

@app.get('/api/device/command')
def next_command(device_id: str, x_device_key: str = Header(default='')):
    require_key(x_device_key, DEVICE_KEY)
    now=time.time()
    with db() as c:
        c.execute("UPDATE commands SET status='expired' WHERE status='pending' AND expires_at<?",(now,))
        row=c.execute("SELECT * FROM commands WHERE device_id=? AND status='pending' AND expires_at>=? ORDER BY created_at DESC LIMIT 1",(device_id,now)).fetchone()
        if row:
            c.execute("UPDATE commands SET status='delivered' WHERE id=?",(row['id'],))
            return dict(row)
    return {'status':'none'}

class Ack(BaseModel):
    command_id: str
    status: str
@app.post('/api/device/ack')
def ack(data: Ack, x_device_key: str = Header(default='')):
    require_key(x_device_key, DEVICE_KEY)
    if data.status not in ('completed','rejected','stopped'): raise HTTPException(422,'Invalid status')
    with db() as c:
        c.execute("UPDATE commands SET status=? WHERE id=? AND status='delivered'",(data.status,data.command_id))
    return {'ok':True}

from fastapi.staticfiles import StaticFiles
app.mount('/',StaticFiles(directory='../frontend',html=True),name='frontend')
