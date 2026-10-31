# ABHEDYA VARAH — Backend Implementation

This is a FastAPI + SQLite backend for the ABHEDYA VARAH flood intelligence platform with enhanced weather monitoring, water-level tracking, flood risk prediction, and infrastructure management.

## Important
This backend now provides enhanced functionality over the original sample-only implementation. Real weather data via Open-Meteo API, water-level monitoring with database storage, and enhanced risk prediction are now operational. However, the system still uses sample data for most operational alerts and requires further integration with official weather services (IMD, NASA IMERG) for complete production deployment.

## Backend Features

### Real Data Integration
- **Weather Monitoring**: Live data via Open-Meteo API (free, no key required)
- **Water-Level Monitoring**: Database storage with station management
- **Flood Risk Prediction**: Enhanced heuristic model with live data integration
- **Infrastructure Monitoring**: Asset management with live status tracking
- **Data Import/Export**: CSV/JSON import pipeline with validation
- **Manual Operations**: Simulated pump/gate control interface

### Enhanced Endpoints
- `GET /api/weather/current` - Current weather from Open-Meteo
- `GET /api/dashboard/summary` - Flood monitoring dashboard (live + sample)
- `GET /api/risk` - Enhanced flood risk prediction (live inputs)
- `GET /api/infrastructure` - Infrastructure asset management
- `GET /api/analytics/historical` - Historical flood data
- `GET /api/alerts` - Alert management
- `POST /api/alerts` - Create new alerts
- `PATCH /api/alerts/{id}/resolve` - Resolve alerts
- `GET /api/water-level-readings` - Water level monitoring
- `POST /api/water-level-readings` - Record water level readings
- `GET /api/water-level-readings/stats` - Water level statistics
- `POST /api/weather-data-import` - Import weather data (CSV/JSON)
- `POST /api/water-level-data-import` - Import water level data (CSV/JSON)
- `GET /api/import-history` - Import history tracking
- `GET /api/alerts/historical` - Historical alerts
- `POST /api/operations/manual-action` - Manual operations simulation
- `GET /` - System overview and API documentation
- `GET /api/health` - System health check

### Data Modes
- **Live**: Real-time data from Open-Meteo API and database
- **Sample**: Built-in demo/sample data for development
- **Demo**: Simulated sensor readings for testing
- **Heuristic**: Model-generated predictions

## Database Schema

Enhanced SQLite schema with new tables:
- `users` - User authentication
- `alerts` - Alert management
- `weather_readings` - Weather observation data (new)
- `water_level_readings` - Water level observations (new)
- `risk_predictions` - Flood risk predictions (new)
- `infrastructure_assets` - Infrastructure asset tracking (new)
- `import_history` - Import operation tracking (new)

## Installation and Setup

### Prerequisites
- Python 3.8+
- pip

### Setup Steps

```powershell
# Navigate to backend directory
cd backend/abhedya_varah_backend

# Create virtual environment
py -m venv .venv

# Activate environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Initialize database
# Run app.py once to create tables, or use FastAPI startup
uvicorn main:app --reload
```

### Environment Variables

Set these environment variables before deployment:

```bash
# JWT secret for authentication (REQUIRED for production)
JWT_SECRET=your-super-secret-key-here

# Frontend URL for CORS restrictions
FRONTEND_URL=https://your-frontend-domain.com

# CORS origins (comma-separated)
CORS_ORIGINS=https://your-frontend-domain.com,http://localhost:3000

# Environment type
definicion ENVIRONMENT=production
```

## Running the Backend

### Development
```bash
cd backend/abhedya_varah_backend
uvicorn main:app --reload
```

### Production (Render)
```bash
cd backend/abhedya_varah_backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

## API Documentation

The API includes built-in FastAPI documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Authentication

Most sensitive endpoints require Bearer token authentication:

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "yourpassword"}'

# Save the access_token from response
curl -X GET "http://localhost:8000/api/protected-endpoint" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Default demo credentials:
- Email: `ops@abhedya.gov.in`
- Password: `abhedya2025`

## Data Import Pipeline

### Weather Data Import
```bash
curl -X POST "http://localhost:8000/api/weather-data-import" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"filename": "weather_data.csv", "data": [...weather records...]}'
```

### Water-Level Data Import
```bash
curl -X POST "http://localhost:8000/api/water-level-data-import" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"filename": "water_levels.csv", "data": [...water records...], "station_mapping": {...}}'
```

## Frontend Integration

The frontend (`frontend/index.html`) needs to be updated to call these endpoints:

### API Configuration
Add this to your frontend JavaScript:
```javascript
const API_BASE_URL = 'http://localhost:8000'  // Change to your backend URL
```

### Example Fetch Calls
```javascript
// Get current weather
fetch(`${API_BASE_URL}/api/weather/current?lat=22.7196&lon=75.8577`)
  .then(response => response.json())
  .then(data => console.log('Weather data:', data))

// Get flood risk prediction
fetch(`${API_BASE_URL}/api/risk?lat=22.7196&lon=75.8577`)
  .then(response => response.json())
  .then(data => console.log('Risk prediction:', data))

// Get water level readings
fetch(`${API_BASE_URL}/api/water-level-readings`)
  .then(response => response.json())
  .then(data => console.log('Water levels:', data))
```

## Deployment Instructions (Render)

### Environment Configuration
Create a `render.yaml` file:
```yaml
services:
  - type: web
    name: abhedya-varah-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port 8000
    envVars:
      - key: JWT_SECRET
        value: your-super-secret-key-here
      - key: ENVIRONMENT
        value: production
      - key: FRONTEND_URL
        value: https://your-frontend-domain.com
      - key: CORS_ORIGINS
        value: https://your-frontend-domain.com
    healthCheck:
      path: /api/health
```

### Database Setup
Render uses SQLite by default. For production with multiple instances:
- Use SQLite with `abhedya_varah.db` in the working directory
- Or configure PostgreSQL connection string

### CORS Configuration
The backend restricts CORS to specific origins for security:
- Update `CORS_ORIGINS` in Render environment variables
- Only allow your deployed frontend domain

## Testing

### API Endpoints Testing
Test all endpoints with these curl commands:

```bash
# Health check
curl -X GET http://localhost:8000/api/health

# Root endpoint
curl -X GET http://localhost:8000/

# Weather data
curl -X GET "http://localhost:8000/api/weather/current?lat=22.7196&lon=75.8577"

# Risk prediction
curl -X GET "http://localhost:8000/api/risk?lat=22.7196&lon=75.8577"

# Infrastructure assets
curl -X GET http://localhost:8000/api/infrastructure

# Historical data
curl -X GET http://localhost:8000/api/analytics/historical

# Alerts
curl -X GET http://localhost:8000/api/alerts
```

### Authentication Testing
```bash
# Register new user
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Test User", "email": "test@example.com", "password": "testpassword123"}'

# Login
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpassword123"}'
```

## Data Requirements

For detailed data import specifications, see `data_requirements.md` in the backend directory.

## Upgrading from Sample-Only Version

### What Changed
1. **Weather Monitoring**: Now uses Open-Meteo API for live data
2. **Water-Level Monitoring**: Database storage and import pipeline
3. **Risk Prediction**: Enhanced with configurable heuristic model
4. **Infrastructure**: Asset tracking with live status
5. **Data Import**: Full CSV/JSON import with validation
6. **Security**: Restricted CORS and authentication requirements

### Backward Compatibility
- All original sample data endpoints still work
- Existing API responses maintain similar structure
- Authentication required for some new endpoints
- Database schema is backward compatible

## Known Limitations

1. **Weather Data**: Only Open-Meteo API integrated; IMD and NASA IMERG APIs need API keys
2. **Data Import**: Large dataset imports may require optimization
3. **Risk Prediction**: Heuristic model needs calibration with real flood events
4. **Hardware Integration**: Pump/gate operations are simulated
5. **Database Performance**: SQLite may need optimization for high-volume data

## Future Enhancements

1. **Integration Plans**:
   - IMD API integration (requires API key)
   - NASA IMERG precipitation data
   - River flow models
   - Weather radar integration

2. **Machine Learning**:
   - Supervised flood prediction models
   - Anomaly detection
   - Time series forecasting

3. **Infrastructure**:
   - Real-time sensor network integration
   - IoT device management
   - Automated pump control

## Troubleshooting

### Common Issues

**Database Errors**:
- Ensure proper file permissions for `abhedya_varah.db`
- Check that all tables exist by running the app once

**CORS Errors**:
- Update `FRONTEND_URL` and `CORS_ORIGINS` environment variables
- Allow your frontend domain in the Render dashboard

**API Key Issues**:
- Add IMD and NASA API keys to environment variables for full integration
- Use Open-Meteo as fallback (no key required)

**Import Errors**:
- Validate CSV/JSON schema before import
- Check data types and required fields
- Ensure proper timestamp formats

### Support

For issues with this backend implementation:
- **Email**: support@abhedya.gov.in
- **GitHub Issues**: Report issues in the ABHEDYA_VARAH repository
- **Documentation**: See `data_requirements.md` for detailed specifications

---

*This backend is part of the ABHEDYA VARAH flood intelligence platform. Built for AI Manthan 2.0 Hackathon. All metrics marked as Live/Historical/Heuristic are based on available data sources and require continuous validation and improvement.*

## Quick Start Summary

1. `cd backend/abhedya_varah_backend`
2. `py -m venv .env && .\venv\Scripts\Activate.ps1`
3. `pip install -r requirements.txt`
4. `uvicorn main:app --reload`
5. Update frontend to use API calls
6. Test all endpoints
7. Deploy to Render with proper environment variables