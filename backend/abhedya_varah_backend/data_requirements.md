# DATA REQUIREMENTS FOR ABHEDYA VARAH

## Overview
This document outlines the data requirements needed to fully operationalize the ABHEDYA VARAH flood intelligence system. The project currently uses simulated/sample data, and these specifications guide users in providing real data to replace the demo values.

## Module 1: Weather Monitoring

### Required Data Sources
- **Open-Meteo API** (free, no API key required)
- **India Meteorological Department (IMD)** - API access required
- **NASA IMERG** - Global precipitation data
- **Local weather station networks** - In-situ measurements

### Required Columns for Weather Data
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `timestamp` | datetime | Exact observation time | `2024-08-15T14:30:00Z` |
| `location_name` | string | Station or region name | `Indore Weather Station` |
| `latitude` | float | Geographic latitude | `22.7196` |
| `longitude` | float | Geographic longitude | `75.8577` |
| `temperature_celsius` | float | Air temperature in °C | `28.5` |
| `humidity_percent` | float | Relative humidity (0-100) | `84.0` |
| `wind_speed_kmh` | float | Wind speed in km/h | `12.0` |
| `wind_direction_degrees` | float | Wind direction (0-360) | `270.0` |
| `rainfall_mm_hour` | float | Precipitation in last hour (mm) | `18.4` |
| `pressure_hpa` | float | Atmospheric pressure (hPa) | `1013.2` |
| `visibility_km` | float | Visibility distance (km) | `10.0` |
| `cloud_cover_percent` | float | Sky coverage (0-100) | `75.0` |
| `forecast_probability_percent` | float | Flood probability forecast (0-100) | `78.0` |
| `source` | string | Data source identifier | `open-meteo`, `imd`, `local` |
| `data_quality_flag` | string | Quality indicator | `good`, `questionable`, `bad` |

### Time Resolution Requirements
- **Current conditions**: Every 5-15 minutes (real-time monitoring)
- **Historical archive**: Daily records for at least 10 years
- **Forecast data**: 6-hour, 24-hour, 72-hour horizons

### Frequency Requirements
- **Critical weather events**: Immediate (5-15 minutes during monsoons)
- **Routine monitoring**: Hourly updates
- **Archive maintenance**: Daily batch processing

## Module 2: Water-Level Monitoring

### Required Data Sources
- **Indian River Commission (IRC) gauges**
- **State water resources departments**
- **Local municipality sensors**
- **Satellite-based water level measurements**

### Required Columns for Water-Level Data
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `timestamp` | datetime | Observation time | `2024-08-15T14:30:00Z` |
| `station_id` | string | Unique station identifier | `KR-04` |
| `station_name` | string | Human-readable station name | `Khan River - Rajwada` |
| `latitude` | float | Station latitude | `22.7179` |
| `longitude` | float | Station longitude | `75.8573` |
| `water_level_meters` | float | Water depth above datum (m) | `3.2` |
| `water_level_status` | string | Operational status | `Normal`, `Watch`, `Alert`, `Critical` |
| `measurement_unit` | string | Unit of measurement | `meters` |
| `gauge_height_reference_meters` | float | Sensor mounting height (m) | `2.5` |
| `flow_rate_cubic_meters_per_second` | float | Water discharge rate | `15.8` |
| `battery_level_percent` | float | Sensor battery (0-100) | `85.0` |
| `data_quality_flag` | string | Measurement quality | `good`, `questionable`, `bad` |
| `upstream_rainfall_mm_24h` | float | Rainfall 24h upstream (mm) | `47.2` |
| `reservoir_level_ratio` | float | Storage capacity ratio (0-1) | `0.62` |
| `source` | string | Data source | `irc`, `state_dept`, `local` |

### Station Requirements
- **Minimum 50 monitoring stations** across target regions
- **Cross-validation with at least 2 sources per critical station**
- **Calibration standards**: ±2mm accuracy for water levels
- **Maintenance schedule**: Quarterly sensor checks

### Data Validation Rules
- **Water level**: Should not exceed danger mark by more than 10%
- **Rate of change**: Maximum 1m/hour increase/decrease for normal conditions
- **Missing data**: Flag readings >6 hours old as stale

## Module 3: Early Flood-Risk Prediction

### Required Input Features
| Feature | Type | Source | Required Range |
|---------|------|--------|----------------|
| `rainfall_intensity_mm_hour` | float | Weather monitoring | 0-200 mm/hr |
| `accumulated_rainfall_mm_24h` | float | Weather monitoring | 0-1000 mm |
| `water_level_meters` | float | Water-level monitoring | 0-20 m |
| `water_level_rate_meters_per_hour` | float | Water-level monitoring | -5 to 5 m/hr |
| `terrain_elevation_meters` | float | DEM data | 100-1000 m |
| `drainage_capacity_cubic_meters_per_second` | float | Infrastructure data | 0-1000 m³/s |
| `waterway_proximity_meters` | float | Infrastructure data | 0-10000 m |
| `soil_saturation_percent` | float | Environmental data | 0-100 |
| `historical_flood_incidents` | integer | Historical database | 0-100+ |

### Model Training Data
- **Training period**: 2010-2023 (14 years)
- **Number of incidents**: 500+ flood events
- **Validation period**: 2024 (held-out test set)
- **Cross-validation**: 5-fold spatial cross-validation

### Performance Requirements
- **Accuracy**: ≥85% for major flood events (>100 incidents)
- **Precision**: ≥80% for medium events (25-100 incidents)
- **Recall**: ≥75% for minor events (<25 incidents)
- **False positive rate**: <10%

### Model Documentation
- **Algorithm**: Hybrid heuristic + machine learning
- **Features**: Top 10 most predictive variables
- **Thresholds**: Configurable risk score cutoffs
- **Confidence intervals**: 95% prediction intervals

## Module 4: Smart Pump and Gate Operations

### Required Infrastructure Assets
| Asset Type | Required Attributes | Example Assets |
|------------|-------------------|----------------|
| **Pumping Stations** | capacity, coordinates, status, operator, telemetry | P-01, P-03, P-12 |
| **Drainage Gates** | opening %age, status, flood risk level, maintenance schedule | N-12, N-23, N-45 |
| **Sluice Gates** | flow capacity, status, flood risk, automation status | SG-01, SG-02, SG-03 |

### Required Columns for Infrastructure Data
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `asset_id` | string | Unique identifier | `P-03` |
| `asset_type` | string | Pump, gate, sluice, barrier | `pump_station` |
| `name` | string | Human-readable name | `Pumping Station P-03` |
| `latitude` | float | Asset location | `22.7196` |
| `longitude` | float | Asset location | `75.8577` |
| `status` | string | Operational status | `OK`, `Monitor`, `Alert` |
| `risk_level` | string | Flood risk level | `Low`, `Moderate`, `High` |
| `capacity_utilization_percent` | float | Current usage (0-100) | `65.0` |
| `last_maintenance_date` | datetime | Last service date | `2024-07-15` |
| `next_scheduled_maintenance_date` | datetime | Next service due | `2024-10-15` |
| `operator_on_duty` | string | Current operator | `A. Sharma` |
| `telemetry_data` | JSON | Sensor readings | `{ "flow": "120 m³/s", "power": "450 kW" }` |
| `timestamp` | datetime | Last update time | `2024-08-15T14:30:00Z` |
| `source` | string | Data source | `sensor_network`, `manual` |

### Operational Requirements
- **Real-time monitoring**: 1-5 second update intervals
- **Alert thresholds**: Configurable flood levels per asset
- **Safety constraints**: Maximum operational limits per asset type
- **Integration requirements**: Interface with physical control systems

## General Data Requirements

### Data Quality Standards
- **Completeness**: >95% for critical parameters
- **Accuracy**: Within specified tolerances for each parameter
- **Consistency**: No temporal gaps >24 hours for operational data
- **Timeliness**: Real-time for monitoring, daily for archives

### Data Storage Requirements
- **Weather data**: 10 years, hourly resolution (≈876,000 records)
- **Water-level data**: 10 years, 15-minute intervals (≈526,000 records per station)
- **Infrastructure data**: Current versions + historical changes
- **Historical incidents**: Complete records with geo-coordinates

### Backup and Recovery
- **Daily automated backups**: Full system snapshot
- **Weekly cold storage**: Archival to secondary storage
- **Disaster recovery**: 4-hour RTO (Recovery Time Objective)

## Import Pipeline Requirements

### Supported Formats
- **CSV**: Comma-separated values with UTF-8 encoding
- **JSON**: Structured records with ISO 8601 timestamps
- **Excel**: .xlsx format with named worksheets

### Import Validation
- **Schema validation**: Required columns and data types
- **Range validation**: Numeric ranges and logical constraints
- **Temporal validation**: Consistent time sequences
- **Duplicate detection**: Identify and handle duplicate records

### Import Processing
- **Progress tracking**: Real-time import progress display
- **Error reporting**: Detailed error messages with row numbers
- **Conflict resolution**: Handle data conflicts automatically
- **Quality assessment**: Post-import data quality report

## Data Privacy and Security

### Sensitive Data Protection
- **Personal data**: Anonymize all personal identifiers
- **Operator information**: Cryptographic storage of contact details
- **Access control**: Role-based access to sensitive data
- **Audit trails**: Complete log of all data access and modifications

### Data Governance
- **Data ownership**: Clear ownership of all data sources
- **Usage rights**: Document commercial and non-commercial usage rights
- **Attribution**: Proper citation for third-party data
- **Licensing**: Verify and document all data licenses

## Next Steps for Data Implementation

1. **Immediate Actions** (1-2 weeks):
   - Set up Open-Meteo API integration (free, no key required)
   - Configure local weather station interfaces
   - Implement water-level database schema

2. **Short-term Goals** (1-3 months):
   - Integrate IMD API (requires API key)
   - Deploy sensor network infrastructure
   - Implement historical data archive

3. **Long-term Goals** (3-12 months):
   - Establish data partnerships with government agencies
   - Implement machine learning model training pipeline
   - Create automated data quality monitoring system

## Current Limitations

**Data Gaps**:
- No real weather API integration beyond Open-Meteo
- Limited water-level monitoring stations
- Historical data gaps in early years (2010-2015)
- Insufficient infrastructure asset data

**Recommendations**:
1. Start with Open-Meteo integration (immediate, no cost)
2. Gradually expand to other APIs as budget allows
3. Implement data collection from local authorities
4. Consider data-as-a-service subscriptions for comprehensive coverage

## Contact for Data Provider Partnerships

For data source questions, please contact:
- **Email**: data-partnerships@abhedya.gov.in
- **Phone**: +91-755-123-4567
- **Address**: ABHEDYA VARAH Headquarters, Acropolis, Indore

---

*This document is version 1.0 and will be updated as the data integration requirements evolve. Please refer to the implementation guide for specific data integration procedures.*