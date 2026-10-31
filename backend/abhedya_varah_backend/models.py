"""Data models and schemas for ABHEDYA VARAH backend"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from decimal import Decimal

class DataSource(str, Enum):
    LIVE = "live"
    SAMPLE = "sample"
    DEMO = "demo"
    HEURISTIC = "heuristic"

class WeatherReading(BaseModel):
    """Weather observation data model"""
    id: Optional[int] = None
    location_name: str = Field(..., min_length=2, max_length=100)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-90, le=90)
    temperature_celsius: Optional[float] = Field(None, gt=-100, lt=60)
    humidity_percent: Optional[float] = Field(None, ge=0, le=100)
    wind_speed_kmh: Optional[float] = Field(None, ge=0)
    wind_direction_degrees: Optional[float] = Field(None, ge=0, le=360)
    rainfall_mm_hour: Optional[float] = Field(None, ge=0)
    pressure_hpa: Optional[float] = Field(None, gt=0)
    visibility_km: Optional[float] = Field(None, gt=0)
    cloud_cover_percent: Optional[float] = Field(None, ge=0, le=100)
    timestamp: datetime = Field(default_factory=datetime.now)
    forecast_probability_percent: Optional[float] = Field(None, ge=0, le=100)
    source: DataSource = DataSource.SAMPLE
    external_id: Optional[str] = None
    data_quality_flag: Optional[str] = None
    created_at: Optional[datetime] = None

    @validator('temperature_celsius', 'humidity_percent', 'wind_speed_kmh', 'rainfall_mm_hour')
    def validate_positive_or_none(cls, v):
        if v is not None and v < 0:
            raise ValueError(f"Value must be positive or None, got {v}")
        return v

    class Config:
        orm_mode = True

class WaterLevelReading(BaseModel):
    """Water level observation data model"""
    id: Optional[int] = None
    station_id: str = Field(..., min_length=1, max_length=50)
    station_name: str = Field(..., min_length=2, max_length=100)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-90, le=90)
    water_level_meters: Optional[float] = Field(None)
    water_level_status: str = Field(default="Normal", description="Normal, Watch, Alert, Critical")
    measurement_unit: str = Field(default="meters")
    gauge_height_reference_meters: Optional[float] = Field(None)
    flow_rate_cubic_meters_per_second: Optional[float] = Field(None, ge=0)
    timestamp: datetime = Field(default_factory=datetime.now)
    source: DataSource = DataSource.SAMPLE
    sensor_id: Optional[str] = None
    battery_level_percent: Optional[float] = Field(None, ge=0, le=100)
    data_quality_flag: Optional[str] = None
    upstream_rainfall_mm_24h: Optional[float] = Field(None, ge=0)
    reservoir_level_ratio: Optional[float] = Field(None, ge=0, le=1)
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class RiskPrediction(BaseModel):
    """Flood risk prediction model"""
    id: Optional[int] = None
    location_name: str = Field(..., min_length=2, max_length=100)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-90, le=90)
    risk_score: int = Field(..., ge=0, le=100)
    risk_level: str = Field(..., description="Low, Moderate, High, Critical")
    prediction_horizon_hours: Optional[int] = Field(None, ge=0, le=168)
    confidence_percent: Optional[float] = Field(None, ge=0, le=100)
    risk_factors: Dict[str, Any] = Field(default={})
    rainfall_intensity_mm_hour: Optional[float] = Field(None, ge=0)
    accumulated_rainfall_mm_24h: Optional[float] = Field(None, ge=0)
    water_level_meters: Optional[float] = Field(None)
    water_level_rate_meters_per_hour: Optional[float] = Field(None)
    terrain_elevation_meters: Optional[float] = Field(None)
    drainage_capacity_cubic_meters_per_second: Optional[float] = Field(None)
    waterway_proximity_meters: Optional[float] = Field(None)
    timestamp: datetime = Field(default_factory=datetime.now)
    valid_until: Optional[datetime] = None
    model_version: str = Field(default="v0.3.heuristic")
    data_source: DataSource = DataSource.HEURISTIC
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class InfrastructureAsset(BaseModel):
    """Infrastructure asset model"""
    id: Optional[int] = None
    asset_id: str = Field(..., min_length=1, max_length=50)
    asset_type: str = Field(..., description="bridge, drain, pump_station, facility")
    name: str = Field(..., min_length=2, max_length=100)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-90, le=90)
    status: str = Field(default="OK", description="OK, Monitor, Alert, Critical")
    risk_level: str = Field(default="Low", description="Low, Moderate, High, Critical")
    location_description: Optional[str] = None
    capacity_utilization_percent: Optional[float] = Field(None, ge=0, le=100)
    last_maintenance_date: Optional[datetime] = None
    next_scheduled_maintenance_date: Optional[datetime] = None
    operator_on_duty: Optional[str] = None
    telemetry_data: Dict[str, Any] = Field(default={})
    timestamp: datetime = Field(default_factory=datetime.now)
    source: DataSource = DataSource.SAMPLE
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class WeatherDataImportRequest(BaseModel):
    """Request model for weather data import"""
    filename: str
    data: List[Dict[str, Any]]
    source_location: Optional[str] = None
    import_mode: str = Field(default="validate_only")

class WaterLevelDataImportRequest(BaseModel):
    """Request model for water level data import"""
    filename: str
    data: List[Dict[str, Any]]
    source_location: Optional[str] = None
    import_mode: str = Field(default="validate_only")
    station_mapping: Optional[Dict[str, str]] = None

class ImportHistory(BaseModel):
    """Import operation history"""
    id: Optional[int] = None
    filename: str
    import_type: str
    records_processed: int
    records_valid: int
    records_invalid: int
    import_status: str = Field(default="pending")
    error_messages: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    user_id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class HistoricalMetrics(BaseModel):
    """Historical metrics for analytics"""
    year: int
    rainfall_mm: float
    flood_incidents: int
    average_water_level_m: float
    max_rainfall_mm: float
    incidents_count: int
    risk_score_average: float