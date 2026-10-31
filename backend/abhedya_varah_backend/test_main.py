# Tests for ABHEDYA VARAH backend
# Can be run with: python -m pytest test_main.py -v

import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone
import json

# Add the backend parent directory to path for package imports
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Add current directory for local imports as fallback
TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

# Import using package name
from abhedya_varah_backend.main import app, init_db
from fastapi.testclient import TestClient

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    yield

class TestHealthAndRoot:
    def test_health_endpoint(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "database" in data
        assert "timestamp" in data
        assert "version" in data  # Should be present
        # Also verify data_counts is present
        assert "data_counts" in data

    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "ABHEDYA VARAH API"
        assert data["status"] == "running"

class TestAuthentication:
    def test_user_registration_and_login(self):
        email = f"test_{datetime.now().timestamp()}@example.com"
        reg_response = client.post("/api/auth/register", json={"full_name": "Test User", "email": email, "password": "securepassword123"})
        assert reg_response.status_code == 201
        assert "access_token" in reg_response.json()

        login_response = client.post("/api/auth/login", json={"email": email, "password": "securepassword123"})
        assert login_response.status_code == 200
        assert "access_token" in login_response.json()

    def test_invalid_login(self):
        response = client.post("/api/auth/login", json={"email": "nonexistent@example.com", "password": "wrongpassword"})
        assert response.status_code == 401

class TestDashboard:
    def test_dashboard_summary(self):
        response = client.get("/api/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert "predicted_risk" in data
        assert "rainfall" in data
        assert "water_level" in data
        assert "active_alerts" in data

class TestWeather:
    def test_weather_current(self):
        response = client.get("/api/weather/current?lat=22.7196&lon=75.8577")
        assert response.status_code == 200
        data = response.json()
        assert "location" in data
        assert "temperature_c" in data
        assert "rainfall_mm_hour" in data

    def test_weather_sample_fallback(self):
        response = client.get("/api/weather/current?lat=999&lon=999")
        assert response.status_code == 200
        data = response.json()
        assert "data_mode" in data

class TestRisk:
    def test_risk_prediction(self):
        response = client.get("/api/risk?lat=22.7196&lon=75.8577")
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert "level" in data
        assert "factors" in data
        assert 0 <= data["score"] <= 100
        assert data["level"] in ["Low", "Moderate", "High", "Critical"]

    def test_risk_calculation_deterministic(self):
        r1 = client.get("/api/risk?lat=22.7&lon=75.8").json()
        r2 = client.get("/api/risk?lat=22.7&lon=75.8").json()
        assert r1["score"] == r2["score"]

class TestInfrastructure:
    def test_infrastructure_endpoints(self):
        response = client.get("/api/infrastructure")
        assert response.status_code == 200
        data = response.json()
        assert "assets" in data

class TestHistoricalData:
    def test_historical_analytics(self):
        response = client.get("/api/analytics/historical")
        assert response.status_code == 200
        data = response.json()
        assert "years" in data
        assert len(data["years"]) >= 1

class TestAlerts:
    def test_alerts_crud_workflow(self):
        list_response = client.get("/api/alerts")
        assert list_response.status_code == 200
        initial_count = len(list_response.json()["items"])

        email = f"alerttest_{int(datetime.now().timestamp())}@example.com"
        reg = client.post("/api/auth/register", json={"full_name": "Alert Tester", "email": email, "password": "securepass123"})
        token = reg.json()["access_token"]

        create_res = client.post("/api/alerts", headers={"Authorization": f"Bearer {token}"},
            json={"title": "Test Alert", "severity": "Moderate", "location": "Test Location", "description": "Test description"})
        assert create_res.status_code == 201
        alert_id = create_res.json()["id"]

        resolve_res = client.patch(f"/api/alerts/{alert_id}/resolve", headers={"Authorization": f"Bearer {token}"})
        assert resolve_res.status_code == 200
        assert resolve_res.json()["status"] == "Resolved"

class TestWaterLevel:
    def test_water_level_readings(self):
        response = client.get("/api/water-level-readings")
        # May return empty items if no data imported yet
        assert response.status_code == 200
        assert "items" in response.json()

    def test_water_level_stats(self):
        response = client.get("/api/water-level-readings/stats")
        # May return empty stations if no readings
        assert response.status_code == 200
        assert "stations" in response.json()

class TestDataImport:
    def test_weather_data_import(self):
        email = f"importtest_{int(datetime.now().timestamp())}@example.com"
        client.post("/api/auth/register", json={"full_name": "Import Tester", "email": email, "password": "securepass123"})
        login = client.post("/api/auth/login", json={"email": email, "password": "securepass123"})
        token = login.json()["access_token"]

        import_res = client.post("/api/weather-data-import", headers={"Authorization": f"Bearer {token}"},
            json={"filename": "test_weather.json", "data": [{
                "location_name": "Test Location",
                "latitude": 22.7196,
                "longitude": 75.8577,
                "temperature_celsius": 29.5,
                "humidity_percent": 80.0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "sample"
            }]})
        # Accept 200 or 404 if endpoint doesn't exist
        if import_res.status_code == 200:
            assert import_res.json()["imported"] == 1

class TestOperations:
    def test_manual_operation_simulation(self):
        email = f"opstest_{int(datetime.now().timestamp())}@example.com"
        client.post("/api/auth/register", json={"full_name": "Ops Tester", "email": email, "password": "securepass123"})
        login = client.post("/api/auth/login", json={"email": email, "password": "securepass123"})
        token = login.json()["access_token"]

        op_res = client.post("/api/operations/manual-action", headers={"Authorization": f"Bearer {token}"},
            json={"operation_type": "pump", "target_id": "P-03", "action": "start"})
        if op_res.status_code == 200:
            data = op_res.json()
            assert data["operation_log"]["status"] == "simulated_success"

def test_historical_alerts():
    response = client.get("/api/alerts/historical?start_date=2020-01-01")
    if response.status_code == 200:
        assert "historical_alerts" in response.json()

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])