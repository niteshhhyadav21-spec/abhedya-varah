from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib, hmac, base64, json, os, sqlite3, secrets

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "abhedya_varah.db"
JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_THIS_DEVELOPMENT_SECRET")
TOKEN_HOURS = 12

app = FastAPI(title="ABHEDYA VARAH API", version="0.1.0")

# For local development. Restrict this to your deployed frontend origin before production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
        con.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            severity TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Active',
            created_at TEXT NOT NULL
        )""")
        count = con.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        if count == 0:
            now = datetime.now(timezone.utc).isoformat()
            con.executemany(
                "INSERT INTO alerts(title,severity,location,description,status,created_at) VALUES(?,?,?,?,?,?)",
                [
                    ("Waterlogging — Bypass Road", "Critical", "Bypass Road", "Sample alert. Verify with an official source.", "Active", now),
                    ("Drain overflow — Palasia N-12", "Moderate", "Palasia", "Sample alert. Verify with an official source.", "Active", now),
                    ("Khan riverside advisory", "Info", "Khan River", "Sample advisory. Verify with an official source.", "Active", now),
                ],
            )

@app.on_event("startup")
def startup():
    init_db()

class RegisterBody(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

class AlertBody(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    severity: str = Field(pattern="^(Info|Low|Moderate|High|Critical)$")
    location: str = Field(min_length=2, max_length=180)
    description: str = Field(min_length=3, max_length=1000)

def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return base64.urlsafe_b64encode(salt).decode() + "." + base64.urlsafe_b64encode(derived).decode()

def verify_password(password: str, stored: str) -> bool:
    try:
        salt_b64, hash_b64 = stored.split(".")
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(hash_b64.encode())
        actual = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False

def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def make_token(user_id: int, email: str) -> str:
    header = b64url(json.dumps({"alg":"HS256","typ":"JWT"}, separators=(",",":")).encode())
    payload = b64url(json.dumps({
        "sub": str(user_id), "email": email,
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS)).timestamp())
    }, separators=(",",":")).encode())
    signing = f"{header}.{payload}".encode()
    signature = b64url(hmac.new(JWT_SECRET.encode(), signing, hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"

def current_user(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sign in required")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        header, payload, signature = token.split(".")
        signing = f"{header}.{payload}".encode()
        expected = b64url(hmac.new(JWT_SECRET.encode(), signing, hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("bad signature")
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if int(data["exp"]) < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("expired")
        return {"id": int(data["sub"]), "email": data["email"]}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.get("/")
def root():
    return {"name": "ABHEDYA VARAH API", "status": "running", "docs": "/docs"}

@app.get("/api/health")
def health():
    return {"status": "ok", "database": "sqlite", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/api/auth/register", status_code=201)
def register(body: RegisterBody):
    with db() as con:
        try:
            cur = con.execute(
                "INSERT INTO users(full_name,email,password_hash,created_at) VALUES(?,?,?,?)",
                (body.full_name.strip(), body.email.lower(), hash_password(body.password), datetime.now(timezone.utc).isoformat())
            )
            user_id = cur.lastrowid
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="An account with this email already exists")
    token = make_token(user_id, body.email.lower())
    return {"access_token": token, "token_type": "bearer", "user": {"id": user_id, "full_name": body.full_name.strip(), "email": body.email.lower()}}

@app.post("/api/auth/login")
def login(body: LoginBody):
    with db() as con:
        user = con.execute("SELECT * FROM users WHERE email=?", (body.email.lower(),)).fetchone()
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = make_token(user["id"], user["email"])
    return {"access_token": token, "token_type": "bearer", "user": {"id": user["id"], "full_name": user["full_name"], "email": user["email"]}}

@app.get("/api/auth/me")
def me(user=Depends(current_user)):
    with db() as con:
        row = con.execute("SELECT id,full_name,email,created_at FROM users WHERE id=?", (user["id"],)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(row)

# These values are deliberately labeled sample/demo data.
# Replace the provider adapters with verified API data before treating them as operational warnings.
@app.get("/api/dashboard/summary")
def dashboard_summary():
    return {
        "data_mode": "sample",
        "predicted_risk": {"score": 64, "level": "Moderate", "horizon_hours": 6},
        "rainfall": {"value": 18.4, "unit": "mm/hr", "classification": "Heavy", "source": "Sample"},
        "water_level": {"value": 3.2, "unit": "m", "station": "KR-04", "status": "Normal", "source": "Sample"},
        "active_alerts": 3,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/weather/current")
def current_weather(lat: float = 22.7196, lon: float = 75.8577):
    return {
        "data_mode": "sample",
        "location": {"lat": lat, "lon": lon},
        "temperature_c": 28,
        "humidity_percent": 84,
        "wind_kmh": 12,
        "rainfall_mm_hour": 18.4,
        "forecast_probability_percent": 78,
        "source": "Sample data — connect a weather provider for live values"
    }

@app.get("/api/risk")
def risk(lat: float = 22.7196, lon: float = 75.8577):
    return {
        "data_mode": "sample",
        "score": 64,
        "level": "Moderate",
        "horizon_hours": 6,
        "factors": [
            {"name":"Rainfall intensity","weight_percent":35,"value_percent":78},
            {"name":"Accumulated 24h rainfall","weight_percent":25,"value_percent":62},
            {"name":"Drainage capacity","weight_percent":20,"value_percent":42},
            {"name":"Terrain and slope","weight_percent":10,"value_percent":34},
            {"name":"Waterway proximity","weight_percent":10,"value_percent":71}
        ],
        "note": "Heuristic demonstration only; not scientifically validated."
    }

@app.get("/api/infrastructure")
def infrastructure():
    return {"data_mode":"sample","assets":[
        {"id":"MR-10","name":"MR-10 Bridge","risk":"High","status":"Monitor"},
        {"id":"N-12","name":"Drain N-12 Palasia","risk":"Moderate","status":"Clog risk"},
        {"id":"P-03","name":"Pumping Station P-03","risk":"Low","status":"OK"},
        {"id":"H-01","name":"MY Hospital Zone","risk":"Low","status":"Safe"}
    ]}

@app.get("/api/analytics/historical")
def historical():
    return {"data_mode":"sample","years":[
        {"year":2018,"rainfall_mm":810,"flood_incidents":400},
        {"year":2019,"rainfall_mm":750,"flood_incidents":600},
        {"year":2020,"rainfall_mm":900,"flood_incidents":190},
        {"year":2021,"rainfall_mm":870,"flood_incidents":800},
        {"year":2022,"rainfall_mm":790,"flood_incidents":400},
        {"year":2023,"rainfall_mm":930,"flood_incidents":990},
        {"year":2024,"rainfall_mm":850,"flood_incidents":600}
    ]}

@app.get("/api/alerts")
def list_alerts(status: str | None = None):
    with db() as con:
        if status:
            rows = con.execute("SELECT * FROM alerts WHERE status=? ORDER BY id DESC", (status,)).fetchall()
        else:
            rows = con.execute("SELECT * FROM alerts ORDER BY id DESC").fetchall()
    return {"items":[dict(row) for row in rows]}

@app.post("/api/alerts", status_code=201)
def create_alert(body: AlertBody, user=Depends(current_user)):
    now = datetime.now(timezone.utc).isoformat()
    with db() as con:
        cur = con.execute(
            "INSERT INTO alerts(title,severity,location,description,status,created_at) VALUES(?,?,?,?,?,?)",
            (body.title, body.severity, body.location, body.description, "Active", now)
        )
        row = con.execute("SELECT * FROM alerts WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row)

@app.patch("/api/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int, user=Depends(current_user)):
    with db() as con:
        cur = con.execute("UPDATE alerts SET status='Resolved' WHERE id=?", (alert_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Alert not found")
        row = con.execute("SELECT * FROM alerts WHERE id=?", (alert_id,)).fetchone()
    return dict(row)
