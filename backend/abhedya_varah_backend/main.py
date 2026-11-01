from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib, hmac, base64, json, os, sqlite3, secrets
import requests
from typing import Optional, List, Dict, Any
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field, validator



BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "abhedya_varah.db"
JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_THIS_DEVELOPMENT_SECRET")
TOKEN_HOURS = 12

# Weather API caching - 10 minute cache for reduced API calls
_weather_cache = {}
_weather_cache_time = None

def get_cached_weather(lat: float, lon: float) -> Optional[Dict]:
    """Get cached weather data if available and not expired."""
    global _weather_cache, _weather_cache_time
    cache_key = f"{lat}:{lon}"
    now = datetime.now(timezone.utc)

    # Check if cache exists and is less than 10 minutes old
    if _weather_cache_time and _weather_cache_time > now - timedelta(minutes=10):
        if cache_key in _weather_cache:
            return _weather_cache[cache_key]
    return None

def set_cached_weather(lat: float, lon: float, data: Dict) -> None:
    """Cache weather data for 10 minutes."""
    global _weather_cache, _weather_cache_time
    cache_key = f"{lat}:{lon}"
    _weather_cache[cache_key] = data
    _weather_cache_time = datetime.now(timezone.utc)

# CORS configuration - restrict to deployed frontend origin
CORS_ORIGINS = [
    "https://imaginative-kulfi-ce1cc9.netlify.app",
    "https://abhedya-varah.onrender.com",
    "http://localhost:3000",
    "http://127.0.0.1:5500",
    "http://localhost:5173",
]
app = FastAPI(title="ABHEDYA VARAH API", version="0.1.0")

# CORS configuration - restrict to deployed frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    expose_headers=["*"],
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
        con.execute("""
        CREATE TABLE IF NOT EXISTS weather_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_name TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            temperature_celsius REAL,
            humidity_percent REAL,
            wind_speed_kmh REAL,
            wind_direction_degrees REAL,
            rainfall_mm_hour REAL,
            pressure_hpa REAL,
            visibility_km REAL,
            cloud_cover_percent REAL,
            timestamp TEXT NOT NULL,
            forecast_probability_percent REAL,
            source TEXT NOT NULL,
            external_id TEXT,
            data_quality_flag TEXT,
            created_at TEXT NOT NULL
        )""")
        con.execute("""
        CREATE TABLE IF NOT EXISTS water_level_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id TEXT NOT NULL,
            station_name TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            water_level_meters REAL,
            water_level_status TEXT DEFAULT 'Normal',
            measurement_unit TEXT DEFAULT 'meters',
            gauge_height_reference_meters REAL,
            flow_rate_cubic_meters_per_second REAL,
            timestamp TEXT NOT NULL,
            source TEXT NOT NULL,
            sensor_id TEXT,
            battery_level_percent REAL,
            data_quality_flag TEXT,
            upstream_rainfall_mm_24h REAL,
            reservoir_level_ratio REAL,
            created_at TEXT NOT NULL
        )""")
        con.execute("""
        CREATE TABLE IF NOT EXISTS risk_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_name TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            risk_score INTEGER NOT NULL,
            risk_level TEXT NOT NULL,
            prediction_horizon_hours INTEGER,
            confidence_percent REAL,
            risk_factors TEXT,
            rainfall_intensity_mm_hour REAL,
            accumulated_rainfall_mm_24h REAL,
            water_level_meters REAL,
            water_level_rate_meters_per_hour REAL,
            terrain_elevation_meters REAL,
            drainage_capacity_cubic_meters_per_second REAL,
            waterway_proximity_meters REAL,
            timestamp TEXT NOT NULL,
            valid_until TEXT,
            model_version TEXT DEFAULT 'v0.3.heuristic',
            data_source TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
        con.execute("""
        CREATE TABLE IF NOT EXISTS infrastructure_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id TEXT NOT NULL UNIQUE,
            asset_type TEXT NOT NULL,
            name TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            status TEXT DEFAULT 'OK',
            risk_level TEXT DEFAULT 'Low',
            location_description TEXT,
            capacity_utilization_percent REAL,
            last_maintenance_date TEXT,
            next_scheduled_maintenance_date TEXT,
            operator_on_duty TEXT,
            telemetry_data TEXT,
            timestamp TEXT NOT NULL,
            source TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
        con.execute("""
        CREATE TABLE IF NOT EXISTS import_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            import_type TEXT NOT NULL,
            records_processed INTEGER NOT NULL,
            records_valid INTEGER NOT NULL,
            records_invalid INTEGER NOT NULL,
            import_status TEXT DEFAULT 'pending',
            error_messages TEXT,
            timestamp TEXT NOT NULL,
            user_id INTEGER,
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

# Environment configuration
PORT = int(os.getenv("PORT", 8000))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

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
    with db() as con:
        # Get system statistics
        users_count = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        alerts_count = con.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]

        return {
            "name": "ABHEDYA VARAH API",
            "status": "running",
            "docs": "/docs",
            "version": app.version,
            "environment": "production" if os.getenv("ENVIRONMENT") == "production" else "development",
            "stats": {
                "registered_users": users_count,
                "active_alerts": alerts_count,
                "uptime": "operational"
            },
            "features": [
                "weather_monitoring",
                "water_level_monitoring",
                "flood_risk_prediction",
                "infrastructure_monitoring",
                "historical_analytics",
                "data_import_export",
                "user_authentication",
                "alert_management"
            ],
            "data_modes": ["live", "sample", "demo", "heuristic"],
            "apis": [
                "/api/weather/current - Current weather data",
                "/api/dashboard/summary - Flood monitoring dashboard",
                "/api/risk - Flood risk predictions",
                "/api/infrastructure - Infrastructure monitoring",
                "/api/analytics/historical - Historical flood data",
                "/api/alerts - Alert management",
                "/api/water-level-readings - Water level monitoring",
                "/api/weather-data-import - Weather data import",
                "/api/water-level-data-import - Water level data import",
                "/api/import-history - Import history tracking"
            ]
        }

@app.get("/api/health")
def health():
    with db() as con:
        # Test database connection
        con.execute("SELECT 1")

        # Get data counts for status
        weather_count = con.execute("SELECT COUNT(*) FROM weather_readings").fetchone()[0]
        water_count = con.execute("SELECT COUNT(*) FROM water_level_readings").fetchone()[0]
        prediction_count = con.execute("SELECT COUNT(*) FROM risk_predictions").fetchone()[0]

        return {
            "status": "ok",
            "database": "sqlite",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data_counts": {
                "weather_readings": weather_count,
                "water_level_readings": water_count,
                "risk_predictions": prediction_count
            },
            "version": app.version,
            "environment": "production" if os.getenv("ENVIRONMENT") == "production" else "development"
        }

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
    with db() as con:
        latest_weather = con.execute(
            """SELECT * FROM weather_readings WHERE source = 'live' ORDER BY timestamp DESC LIMIT 1"""
        ).fetchone()

        latest_water = con.execute(
            """SELECT * FROM water_level_readings WHERE source = 'live' ORDER BY timestamp DESC LIMIT 1"""
        ).fetchone()

        latest_risk = con.execute(
            """SELECT * FROM risk_predictions ORDER BY timestamp DESC LIMIT 1"""
        ).fetchone()

        active_alerts = con.execute(
            """SELECT COUNT(*) FROM alerts WHERE status = 'Active'"""
        ).fetchone()[0]

        response = {
            "data_mode": "sample",
            "predicted_risk": {
                "score": latest_risk["risk_score"] if latest_risk else 64,
                "level": latest_risk["risk_level"] if latest_risk else "Moderate",
                "horizon_hours": latest_risk["prediction_horizon_hours"] if latest_risk else 6,
                "confidence": latest_risk["confidence_percent"] if latest_risk else 75
            },
            "rainfall": {
                "value": latest_weather["rainfall_mm_hour"] if latest_weather else 18.4,
                "unit": "mm/hr",
                "classification": "Heavy" if (latest_weather and latest_weather["rainfall_mm_hour"] and latest_weather["rainfall_mm_hour"] > 15) else "Moderate",
                "source": latest_weather["source"] if latest_weather else "Sample",
                "timestamp": latest_weather["timestamp"] if latest_weather else datetime.now(timezone.utc).isoformat()
            },
            "water_level": {
                "value": latest_water["water_level_meters"] if latest_water else 3.2,
                "unit": "m",
                "station": latest_water["station_name"] if latest_water else "KR-04",
                "status": latest_water["water_level_status"] if latest_water else "Normal",
                "source": latest_water["source"] if latest_water else "Sample",
                "timestamp": latest_water["timestamp"] if latest_water else datetime.now(timezone.utc).isoformat()
            },
            "active_alerts": active_alerts,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        # Add live data if available
        if latest_weather:
            response["weather_live"] = True
        if latest_water:
            response["water_level_live"] = True

        return response

@app.get("/api/weather/current")
def current_weather(lat: float = 22.7196, lon: float = 75.8577):
    """Get current weather data from Open-Meteo API (free, no key required)

    Uses 10-minute caching to reduce API requests.
    Returns 'live' when Open-Meteo responds successfully,
    'cached' when using cached data (< 10 min old),
    'sample' or 'unavailable' when cache expires and API fails.
    """
    # Check for valid cached data first
    cached = get_cached_weather(lat, lon)
    if cached:
        return cached

    # Validate coordinates
    if lat is None or lon is None:
        lat, lon = 22.7196, 75.8577  # Default to Indore

    try:
        # Open-Meteo API provides free weather data
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relativehumidity_2m,wind_speed_10m,wind_direction_10m,precipitation",
            "hourly": "precipitation,weather_code",
            "timezone": "auto"
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Parse Open-Meteo response
        current = data.get("current", {})
        timezone_info = data.get("timezone", "UTC")

        # Validate we got actual data from the provider
        if "temperature_2m" not in current:
            raise ValueError("Incomplete weather data from provider")

        # Build result with provider data
        result = {
            "data_mode": "live",
            "location": {"lat": lat, "lon": lon},
            "temperature_c": current.get("temperature_2m"),
            "humidity_percent": current.get("relativehumidity_2m"),
            "wind_kmh": current.get("wind_speed_10m", 0) * 3.6,  # Convert m/s to km/h
            "wind_direction_degrees": current.get("wind_direction_10m"),
            "rainfall_mm_hour": current.get("precipitation", 0),  # Zero is valid
            "source": "Open-Meteo API (live)",
            "timestamp": data.get("time", datetime.now(timezone.utc).isoformat()),
            "timezone": timezone_info,
            "provider": "open-meteo",
            "weather_code": current.get("weather_code"),
            "units": data.get("current_units", {})
        }

        # Cache the result
        set_cached_weather(lat, lon, result)

        # Store in database
        try:
            with db() as con:
                con.execute("""
                INSERT INTO weather_readings
                (location_name, latitude, longitude, temperature_celsius, humidity_percent,
                 wind_speed_kmh, wind_direction_degrees, rainfall_mm_hour, timestamp,
                 forecast_probability_percent, source, external_id, data_quality_flag, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    f"Lat {lat}, Lon {lon}", lat, lon,
                    result.get("temperature_c"), result.get("humidity_percent"),
                    result.get("wind_kmh"), result.get("wind_direction_degrees"),
                    result.get("rainfall_mm_hour"), result.get("timestamp"),
                    78,  # Will be enhanced with cached hourly data if available
                    "live", "open-meteo", False,  # data_quality_flag: False = good
                    datetime.now(timezone.utc).isoformat()
                ))
        except Exception:
            pass  # Database storage failed, but don't break the API response

        return result

    except requests.Timeout:
        # Try to return cached data if available
        if cached:
            cached["data_mode"] = "cached"
            cached["note"] = "Cache used due to API timeout"
            return cached
        return {
            "data_mode": "unavailable",
            "location": {"lat": lat, "lon": lon},
            "temperature_c": None,
            "humidity_percent": None,
            "wind_kmh": None,
            "wind_direction_degrees": None,
            "rainfall_mm_hour": None,
            "source": "Weather provider unavailable (timeout)",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": "open-meteo",
            "error": "Request timeout"
        }
    except Exception as e:
        # Try to return cached data if available
        if cached:
            cached["data_mode"] = "cached"
            cached["note"] = "Cache used due to API error"
            return cached
        return {
            "data_mode": "unavailable",
            "location": {"lat": lat, "lon": lon},
            "temperature_c": None,
            "humidity_percent": None,
            "wind_kmh": None,
            "wind_direction_degrees": None,
            "rainfall_mm_hour": None,
            "source": f"Weather provider unavailable: {str(e)[:50]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": "open-meteo",
            "error": f"Request error: {str(e)[:50]}"
        }

@app.get("/api/risk")
def risk(lat: float = 22.7196, lon: float = 75.8577):
    """Enhanced flood risk prediction with live data integration"""
    with db() as con:
        # Get latest live data
        latest_weather = con.execute(
            """SELECT * FROM weather_readings WHERE source = 'live' ORDER BY timestamp DESC LIMIT 1"""
        ).fetchone()

        latest_water = con.execute(
            """SELECT * FROM water_level_readings WHERE source = 'live' ORDER BY timestamp DESC LIMIT 1"""
        ).fetchone()

        # Get heuristic prediction
        latest_prediction = con.execute(
            """SELECT * FROM risk_predictions ORDER BY timestamp DESC LIMIT 1"""
        ).fetchone()

        # Calculate risk based on live data if available
        rainfall = latest_weather["rainfall_mm_hour"] if latest_weather else 18.4
        water_level = latest_water["water_level_meters"] if latest_water else 3.2

        # Enhanced heuristic calculation with configurable weights
        base_score = 50  # Base risk score

        # Rainfall intensity factor (35% weight)
        rainfall_factor = min(100, max(0, (rainfall - 5) * 8)) if rainfall > 5 else 0
        rainfall_score = rainfall_factor * 0.35

        # Water level factor (25% weight)
        water_level_factor = min(100, (water_level / 5) * 100) if water_level else 50
        water_score = water_level_factor * 0.25

        # Historical incidents factor (20% weight)
        historical_score = 62 * 0.20

        # Terrain factor (10% weight) - use elevation if available
        terrain_score = 34 * 0.10

        # Drainage factor (10% weight) - inverse of water level
        drainage_score = ((100 - water_level_factor) if water_level else 50) * 0.10

        # Total calculated score
        total_score = base_score + rainfall_score + water_score + historical_score + terrain_score + drainage_score

        # Determine risk level
        if total_score >= 80:
            risk_level = "Critical"
        elif total_score >= 65:
            risk_level = "High"
        elif total_score >= 45:
            risk_level = "Moderate"
        else:
            risk_level = "Low"

        # Get or create prediction record
        if latest_prediction:
            # Update existing prediction
            con.execute("""
            UPDATE risk_predictions
            SET risk_score = ?, risk_level = ?, rainfall_intensity_mm_hour = ?,
                accumulated_rainfall_mm_24h = ?, water_level_meters = ?,
                confidence_percent = ?
            WHERE id = ?
            """, (
                int(total_score), risk_level, rainfall, rainfall * 2,
                water_level, 85 - (int(total_score) // 2), latest_prediction["id"]
            ))
            prediction_id = latest_prediction["id"]
        else:
            # Create new prediction
            now = datetime.now(timezone.utc).isoformat()
            con.execute("""
            INSERT INTO risk_predictions
            (location_name, latitude, longitude, risk_score, risk_level,
             prediction_horizon_hours, confidence_percent, risk_factors,
             rainfall_intensity_mm_hour, accumulated_rainfall_mm_24h,
             water_level_meters, terrain_elevation_meters, data_source, timestamp, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"Lat {lat}, Lon {lon}", lat, lon, int(total_score), risk_level,
                6, 85 - (int(total_score) // 2),
                json.dumps({
                    "Rainfall intensity": {"weight": 35, "value": min(100, max(0, (rainfall - 5) * 8)) if rainfall > 5 else 0},
                    "Accumulated 24h rainfall": {"weight": 25, "value": min(100, rainfall * 2)},
                    "Drainage capacity": {"weight": 20, "value": max(0, 100 - water_level_factor) if water_level else 50},
                    "Terrain and slope": {"weight": 10, "value": 34},
                    "Waterway proximity": {"weight": 10, "value": 71}
                }),
                rainfall, min(100, rainfall * 2), water_level, 553,
                DataSource.HEURISTIC.value, now, now
            ))
            prediction_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Get updated prediction for response
        updated_prediction = con.execute(
            "SELECT * FROM risk_predictions WHERE id = ?", (prediction_id,)
        ).fetchone()

        factors = []
        if updated_prediction["risk_factors"]:
            try:
                factors_data = json.loads(updated_prediction["risk_factors"])
                for name, data in factors_data.items():
                    factors.append({
                        "name": name,
                        "weight_percent": data["weight"],
                        "value_percent": data["value"]
                    })
            except:
                # Fallback to default factors
                factors = [
                    {"name": "Rainfall intensity", "weight_percent": 35, "value_percent": min(100, max(0, (rainfall - 5) * 8)) if rainfall > 5 else 0},
                    {"name": "Accumulated 24h rainfall", "weight_percent": 25, "value_percent": min(100, rainfall * 2)},
                    {"name": "Drainage capacity", "weight_percent": 20, "value_percent": max(0, 100 - water_level_factor) if water_level else 50},
                    {"name": "Terrain and slope", "weight_percent": 10, "value_percent": 34},
                    {"name": "Waterway proximity", "weight_percent": 10, "value_percent": 71}
                ]

        return {
            "data_mode": "heuristic" if updated_prediction else "sample",
            "score": int(total_score),
            "level": risk_level,
            "horizon_hours": 6,
            "confidence": 85 - (int(total_score) // 2),
            "factors": factors,
            "note": "Heuristic calculation using live weather and water level data. Not scientifically validated.",
            "live_data_used": {
                "rainfall_mm_hour": rainfall,
                "water_level_meters": water_level,
                "prediction_id": prediction_id
            }
        }

@app.get("/api/infrastructure")
def infrastructure():
    """Get infrastructure assets with live data support"""
    with db() as con:
        # Get live infrastructure assets from database
        assets = con.execute("""
        SELECT * FROM infrastructure_assets
        WHERE source = 'live'
        ORDER BY risk_level DESC, timestamp DESC
        """).fetchall()

        # If no live assets, return sample data
        if not assets:
            return {"data_mode":"sample","assets":[
                {"id":"MR-10","name":"MR-10 Bridge","risk":"High","status":"Monitor","location":"MR-10 km 4.2"},
                {"id":"N-12","name":"Drain N-12 Palasia","risk":"Moderate","status":"Clog risk","location":"Palasia • 1.2 km"},
                {"id":"P-03","name":"Pumping Station P-03","risk":"Low","status":"OK","location":"Khan East • Active"},
                {"id":"H-01","name":"MY Hospital Zone","risk":"Low","status":"Safe","location":"Critical • Low exposure"},
                {"id":"KN-07","name":"Kanha Canal","risk":"Moderate","status":"Watch","location":"Jawahar Marg"},
                {"id":"RG-11","name":"Rain Gauge RG-11","risk":"Low","status":"OK","location":"Sukhliya"}
            ]}

        # Convert database records to response format
        response_assets = []
        for asset in assets:
            response_assets.append({
                "id": asset["asset_id"],
                "name": asset["name"],
                "risk": asset["risk_level"],
                "status": asset["status"],
                "location": asset["location_description"] or "Indore, MP",
                "capacity": asset["capacity_utilization_percent"],
                "last_maintenance": asset["last_maintenance_date"],
                "source": asset["source"],
                "coordinates": {
                    "latitude": asset["latitude"],
                    "longitude": asset["longitude"]
                }
            })

        return {"data_mode":"live", "assets": response_assets}

@app.get("/api/analytics/historical")
def historical():
    """Get historical data from database with fallback to sample data"""
    with db() as con:
        # Try to get historical metrics from database
        try:
            metrics = con.execute("""
            SELECT * FROM historical_metrics
            ORDER BY year DESC
            LIMIT 10
            """).fetchall()

            if metrics:
                response_years = []
                for metric in metrics:
                    response_years.append({
                        "year": metric["year"],
                        "rainfall_mm": metric["rainfall_mm"],
                        "flood_incidents": metric["flood_incidents"],
                        "average_water_level_m": metric["average_water_level_m"],
                        "max_rainfall_mm": metric["max_rainfall_mm"],
                        "incidents_count": metric["incidents_count"],
                        "risk_score_average": metric["risk_score_average"],
                        "source": "historical"
                    })
                return {"data_mode":"historical", "years": response_years}
        except:
            pass

        # Fallback to sample data
        return {"data_mode":"sample","years":[
            {"year":2018,"rainfall_mm":810,"flood_incidents":400,"average_water_level_m":2.8,"max_rainfall_mm":950,"incidents_count":410,"risk_score_average":62},
            {"year":2019,"rainfall_mm":750,"flood_incidents":600,"average_water_level_m":3.2,"max_rainfall_mm":920,"incidents_count":620,"risk_score_average":68},
            {"year":2020,"rainfall_mm":900,"flood_incidents":190,"average_water_level_m":2.9,"max_rainfall_mm":1050,"incidents_count":210,"risk_score_average":58},
            {"year":2021,"rainfall_mm":870,"flood_incidents":800,"average_water_level_m":3.5,"max_rainfall_mm":980,"incidents_count":840,"risk_score_average":72},
            {"year":2022,"rainfall_mm":790,"flood_incidents":400,"average_water_level_m":3.1,"max_rainfall_mm":890,"incidents_count":430,"risk_score_average":65},
            {"year":2023,"rainfall_mm":930,"flood_incidents":990,"average_water_level_m":3.8,"max_rainfall_mm":1100,"incidents_count":1020,"risk_score_average":78},
            {"year":2024,"rainfall_mm":850,"flood_incidents":600,"average_water_level_m":3.4,"max_rainfall_mm":970,"incidents_count":650,"risk_score_average":70}
        ]}

@app.get("/api/alerts")
def list_alerts(status: str | None = None):
    with db() as con:
        if status:
            rows = con.execute("SELECT * FROM alerts WHERE status=? ORDER BY id DESC", (status,)).fetchall()
        else:
            rows = con.execute("SELECT * FROM alerts ORDER BY id DESC").fetchall()
        return {"items":[dict(row) for row in rows]}

@app.get("/api/water-level-readings")
def list_water_level_readings(station_id: Optional[str] = None, limit: int = 100):
    """Get water level readings with filtering"""
    with db() as con:
        if station_id:
            rows = con.execute(
                "SELECT * FROM water_level_readings WHERE station_id = ? ORDER BY timestamp DESC LIMIT ?",
                (station_id, limit)
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM water_level_readings ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return {"items":[dict(row) for row in rows]}

@app.post("/api/water-level-readings")
def create_water_level_reading(body: WaterLevelReading):
    """Create a new water level reading"""
    now = datetime.now(timezone.utc).isoformat()
    with db() as con:
        cur = con.execute(
            """INSERT INTO water_level_readings
            (station_id, station_name, latitude, longitude, water_level_meters,
             water_level_status, measurement_unit, gauge_height_reference_meters,
             flow_rate_cubic_meters_per_second, timestamp, source, sensor_id,
             battery_level_percent, data_quality_flag, upstream_rainfall_mm_24h,
             reservoir_level_ratio, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                body.station_id, body.station_name, body.latitude, body.longitude,
                body.water_level_meters, body.water_level_status, body.measurement_unit,
                body.gauge_height_reference_meters, body.flow_rate_cubic_meters_per_second,
                body.timestamp, body.source.value, body.sensor_id, body.battery_level_percent,
                body.data_quality_flag, body.upstream_rainfall_mm_24h,
                body.reservoir_level_ratio, now
            )
        )
        row = con.execute("SELECT * FROM water_level_readings WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row)

@app.get("/api/water-level-readings/stats")
def get_water_level_stats():
    """Get water level statistics for dashboard"""
    with db() as con:
        # Get latest readings per station
        stations = con.execute(
            """SELECT DISTINCT station_id FROM water_level_readings ORDER BY station_id"""
        ).fetchall()

        stats = []
        for station in stations:
            latest = con.execute(
                """SELECT * FROM water_level_readings WHERE station_id = ? ORDER BY timestamp DESC LIMIT 1""",
                (station["station_id"],)
            ).fetchone()

            if latest:
                stats.append({
                    "station_id": latest["station_id"],
                    "station_name": latest["station_name"],
                    "water_level_meters": latest["water_level_meters"],
                    "water_level_status": latest["water_level_status"],
                    "timestamp": latest["timestamp"],
                    "source": latest["source"]
                })

        return {"stations": stats}

@app.post("/api/weather-data-import")
def import_weather_data(request: WeatherDataImportRequest, user=Depends(current_user)):
    """Import weather data (CSV/JSON)"""
    now = datetime.now(timezone.utc).isoformat()
    records_processed = len(request.data)
    records_valid = 0
    records_invalid = 0
    error_messages = []

    for i, record in enumerate(request.data):
        try:
            # Validate and store weather reading
            weather_record = WeatherReading(**record, source=DataSource.LIVE)

            with db() as con:
                con.execute("""
                INSERT INTO weather_readings
                (location_name, latitude, longitude, temperature_celsius, humidity_percent,
                 wind_speed_kmh, wind_direction_degrees, rainfall_mm_hour, pressure_hpa,
                 visibility_km, cloud_cover_percent, timestamp, forecast_probability_percent,
                 source, external_id, data_quality_flag, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    weather_record.location_name, weather_record.latitude, weather_record.longitude,
                    weather_record.temperature_celsius, weather_record.humidity_percent,
                    weather_record.wind_speed_kmh, weather_record.wind_direction_degrees,
                    weather_record.rainfall_mm_hour, weather_record.pressure_hpa,
                    weather_record.visibility_km, weather_record.cloud_cover_percent,
                    weather_record.timestamp, weather_record.forecast_probability_percent,
                    weather_record.source.value, weather_record.external_id,
                    weather_record.data_quality_flag or "good", now
                ))
            records_valid += 1
        except Exception as e:
            records_invalid += 1
            error_messages.append(f"Row {i+1}: {str(e)}")

    # Record import history
    with db() as con:
        con.execute("""
        INSERT INTO import_history
        (filename, import_type, records_processed, records_valid, records_invalid,
         import_status, error_messages, timestamp, user_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request.filename, "weather_data", records_processed, records_valid,
            records_invalid, "completed" if records_invalid == 0 else "completed_with_errors",
            "; ".join(error_messages) if error_messages else None, now,
            user.get("id"), now
        ))

    return {
        "imported": records_valid,
        "errors": records_invalid,
        "filename": request.filename,
        "status": "completed" if records_invalid == 0 else "completed_with_errors",
        "errors": error_messages if error_messages else []
    }

@app.post("/api/water-level-data-import")
def import_water_level_data(request: WaterLevelDataImportRequest, user=Depends(current_user)):
    """Import water level data (CSV/JSON)"""
    now = datetime.now(timezone.utc).isoformat()
    records_processed = len(request.data)
    records_valid = 0
    records_invalid = 0
    error_messages = []

    # Default station mapping for demo data
    default_station_mapping = {
        "KR-04": "Khan River - Rajwada",
        "SR-02": "Saraswati - Jawahar Marg",
        "KN-07": "Kanha Canal",
        "RG-11": "Rain Gauge Sukhliya"
    }

    for i, record in enumerate(request.data):
        try:
            # Apply station mapping if provided
            if "station_id" in record and request.station_mapping:
                record["station_name"] = request.station_mapping.get(record["station_id"], record["station_id"])
            elif "station_id" in record:
                record["station_name"] = default_station_mapping.get(record["station_id"], record["station_id"])

            # Validate and store water level reading
            water_record = WaterLevelReading(**record, source=DataSource.LIVE)

            with db() as con:
                con.execute("""
                INSERT INTO water_level_readings
                (station_id, station_name, latitude, longitude, water_level_meters,
                 water_level_status, measurement_unit, gauge_height_reference_meters,
                 flow_rate_cubic_meters_per_second, timestamp, source, sensor_id,
                 battery_level_percent, data_quality_flag, upstream_rainfall_mm_24h,
                 reservoir_level_ratio, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    water_record.station_id, water_record.station_name, water_record.latitude,
                    water_record.longitude, water_record.water_level_meters,
                    water_record.water_level_status, water_record.measurement_unit,
                    water_record.gauge_height_reference_meters, water_record.flow_rate_cubic_meters_per_second,
                    water_record.timestamp, water_record.source.value, water_record.sensor_id,
                    water_record.battery_level_percent, water_record.data_quality_flag,
                    water_record.upstream_rainfall_mm_24h, water_record.reservoir_level_ratio,
                    now
                ))
            records_valid += 1
        except Exception as e:
            records_invalid += 1
            error_messages.append(f"Row {i+1}: {str(e)}")

    # Record import history
    with db() as con:
        con.execute("""
        INSERT INTO import_history
        (filename, import_type, records_processed, records_valid, records_invalid,
         import_status, error_messages, timestamp, user_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request.filename, "water_level_data", records_processed, records_valid,
            records_invalid, "completed" if records_invalid == 0 else "completed_with_errors",
            "; ".join(error_messages) if error_messages else None, now,
            user.get("id"), now
        ))

    return {
        "imported": records_valid,
        "errors": records_invalid,
        "filename": request.filename,
        "status": "completed" if records_invalid == 0 else "completed_with_errors",
        "errors": error_messages if error_messages else []
    }

@app.get("/api/import-history")
def get_import_history(import_type: Optional[str] = None):
    """Get import history"""
    with db() as con:
        if import_type:
            rows = con.execute(
                "SELECT * FROM import_history WHERE import_type = ? ORDER BY timestamp DESC",
                (import_type,)
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM import_history ORDER BY timestamp DESC"
            ).fetchall()
        return {"imports":[dict(row) for row in rows]}

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

@app.post("/api/operations/manual-action")
def manual_operation_action(body: Dict[str, Any], user=Depends(current_user)):
    """Handle manual pump/gate operations (simulated)"""
    operation_type = body.get("operation_type")
    target_id = body.get("target_id")
    action = body.get("action")

    # Simulate operation
    operation_log = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation_type": operation_type,
        "target_id": target_id,
        "action": action,
        "status": "simulated_success",
        "user_id": user["id"],
        "manual_override": True,
        "safety_checks_passed": True,
        "risk_level": "low"
    }

    return {
        "operation_log": operation_log,
        "message": f"Simulated {action} operation on {operation_type} {target_id} completed successfully",
        "note": "This is a simulated operation for demonstration. Real hardware integration required for production use."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)

