import pytest
import json
from unittest.mock import AsyncMock, patch, Mock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from models.modbus_controller import ModbusController
from models.modbus_point import ModbusPoint
from api.modbus.schema import PointType, ConfigFormat
from main import app
from extensions.modbus import get_modbus


class TestModbusControllerAPI:
    
    @pytest.mark.asyncio
    async def test_create_controller_success(self, client: AsyncClient, test_db_session: AsyncSession):
        payload = {
            "name": "Test Controller",
            "host": "192.168.1.100",
            "port": 502,
            "timeout": 10
        }
        
        response = await client.post("/api/modbus/controllers", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "Controller created successfully"
        assert data["data"]["name"] == "Test Controller"
        assert data["data"]["host"] == "192.168.1.100"
        assert data["data"]["port"] == 502
        assert data["data"]["status"] is True
    
    @pytest.mark.asyncio
    async def test_create_controller_connection_failed(self, test_db_session: AsyncSession):
        mock_modbus = AsyncMock()
        
        def mock_create_tcp(host, port, timeout=30):
            client_id = f"tcp_{host}_{port}"
            mock_client = Mock()
            mock_client.connected = False
            mock_client.is_socket_open.return_value = False
            mock_modbus.clients[client_id] = mock_client
            mock_modbus.client_status[client_id] = False
            return client_id
        
        mock_modbus.create_tcp.side_effect = mock_create_tcp
        
        async def mock_connect(client_id):
            return False
        
        mock_modbus.connect = mock_connect
        mock_modbus.disconnect = Mock(return_value=None)
        mock_modbus.clients = {}
        mock_modbus.client_status = {}
        mock_modbus._initialized = False
        mock_modbus.controller_mapping = {}
        
        from httpx import AsyncClient, ASGITransport
        from main import app
        from core.dependencies import get_db
        
        with patch('extensions.modbus.get_modbus', return_value=mock_modbus), \
             patch('api.modbus.controller.get_modbus', return_value=mock_modbus), \
             patch('api.modbus.services.ModbusManager', return_value=mock_modbus), \
             patch('extensions.modbus.ModbusManager', return_value=mock_modbus):
            
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, 
                base_url="http://testserver",
                timeout=30.0
            ) as ac:
                payload = {
                    "name": "Failed Controller",
                    "host": "192.168.1.999",
                    "port": 502,
                    "timeout": 5
                }
                
                response = await ac.post("/api/modbus/controllers", json=payload)
                
                assert response.status_code == 400
                data = response.json()
                error_message = data.get("detail") or data.get("message", "")
                assert "Connection test failed" in error_message or "Unable to connect" in error_message
    
    @pytest.mark.asyncio
    async def test_get_controllers_empty(self, client: AsyncClient, test_db_session: AsyncSession):
        response = await client.get("/api/modbus/controllers")
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["total"] == 0
        assert data["data"]["controllers"] == []
    
    @pytest.mark.asyncio
    async def test_get_controllers_with_filters(self, client: AsyncClient, test_db_session: AsyncSession):
        controller1 = ModbusController(
            name="Controller 1",
            host="192.168.1.100",
            port=502,
            timeout=10,
            status=True
        )
        controller2 = ModbusController(
            name="Controller 2",
            host="192.168.1.101",
            port=502,
            timeout=5,
            status=False
        )
        
        test_db_session.add(controller1)
        test_db_session.add(controller2)
        await test_db_session.commit()
        
        response = await client.get("/api/modbus/controllers?status=true")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 1
        assert data["data"]["controllers"][0]["name"] == "Controller 1"
        
        response = await client.get("/api/modbus/controllers?name=Controller")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 2
    
    @pytest.mark.asyncio
    async def test_update_controller_success(self, client: AsyncClient, test_db_session: AsyncSession):
        controller = ModbusController(
            name="Original Name",
            host="192.168.1.100",
            port=502,
            timeout=10,
            status=True
        )
        test_db_session.add(controller)
        await test_db_session.commit()
        
        payload = {
            "name": "Updated Name",
            "host": "192.168.1.200",
            "port": 503,
            "timeout": 15
        }
        
        response = await client.put(f"/api/modbus/controllers/{controller.id}", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["name"] == "Updated Name"
        assert data["data"]["host"] == "192.168.1.200"
        assert data["data"]["port"] == 503
    
    @pytest.mark.asyncio
    async def test_update_controller_not_found(self, client: AsyncClient, test_db_session: AsyncSession):
        payload = {"name": "Updated Name"}
        
        response = await client.put("/api/modbus/controllers/non-existent-id", json=payload)
        
        assert response.status_code == 404
        data = response.json()
        error_message = data.get("detail") or data.get("message", "")
        assert "Controller not found" in error_message
    
    @pytest.mark.asyncio
    async def test_delete_controller_success(self, client: AsyncClient, test_db_session: AsyncSession):
        controller = ModbusController(
            name="To Delete",
            host="192.168.1.100",
            port=502,
            timeout=10,
            status=True
        )
        test_db_session.add(controller)
        await test_db_session.commit()
        
        response = await client.delete(f"/api/modbus/controllers/{controller.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "Controller deleted successfully"
    
    @pytest.mark.asyncio
    async def test_delete_controller_not_found(self, client: AsyncClient, test_db_session: AsyncSession):
        response = await client.delete("/api/modbus/controllers/non-existent-id")
        
        assert response.status_code == 404
        data = response.json()
        error_message = data.get("detail") or data.get("message", "")
        assert "Controller not found" in error_message
    
    @pytest.mark.asyncio
    async def test_test_controller_success(self, client: AsyncClient):
        payload = {
            "name": "Test Controller",
            "host": "192.168.1.100",
            "port": 502,
            "timeout": 10
        }
        
        response = await client.post("/api/modbus/controllers/test", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["connected"] is True
        assert data["data"]["host"] == "192.168.1.100"
        assert data["data"]["port"] == 502


class TestModbusPointAPI:
    
    @pytest.mark.asyncio
    async def test_create_points_batch_success(self, client: AsyncClient, test_db_session: AsyncSession):
        controller = ModbusController(
            name="Test Controller",
            host="192.168.1.100",
            port=502,
            timeout=10,
            status=True
        )
        test_db_session.add(controller)
        await test_db_session.commit()
        
        payload = {
            "controller_id": controller.id,
            "points": [
                {
                    "name": "Temperature 1",
                    "description": "Boiler temperature sensor",
                    "type": "holding_register",
                    "data_type": "uint16",
                    "address": 40001,
                    "len": 1,
                    "unit_id": 1,
                    "formula": "x * 0.1",
                    "unit": "°C",
                    "min_value": 0.0,
                    "max_value": 100.0
                },
                {
                    "name": "Pressure 1",
                    "description": "System pressure",
                    "type": "input_register",
                    "data_type": "uint16",
                    "address": 30001,
                    "len": 1,
                    "unit_id": 1,
                    "formula": None,
                    "unit": "bar",
                    "min_value": 0.0,
                    "max_value": 10.0
                }
            ]
        }
        
        response = await client.post("/api/modbus/points/batch", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["total"] == 2
        assert len(data["data"]["points"]) == 2
        assert data["data"]["points"][0]["name"] == "Temperature 1"
        assert data["data"]["points"][1]["name"] == "Pressure 1"
    
    @pytest.mark.asyncio
    async def test_create_points_batch_controller_not_found(self, client: AsyncClient, test_db_session: AsyncSession):
        payload = {
            "controller_id": "non-existent-controller",
            "points": [
                {
                    "name": "Test Point",
                    "type": "holding_register",
                    "data_type": "uint16",
                    "address": 40001
                }
            ]
        }
        
        response = await client.post("/api/modbus/points/batch", json=payload)
        
        assert response.status_code == 404
        data = response.json()
        error_message = data.get("detail") or data.get("message", "")
        assert "Controller not found" in error_message
    
    @pytest.mark.asyncio
    async def test_get_points_by_controller(self, client: AsyncClient, test_db_session: AsyncSession):
        controller = ModbusController(
            name="Test Controller",
            host="192.168.1.100",
            port=502,
            timeout=10,
            status=True
        )
        test_db_session.add(controller)
        await test_db_session.commit()
        
        point1 = ModbusPoint(
            controller_id=controller.id,
            name="Temperature 1",
            type="holding_register",
            data_type="uint16",
            address=40001,
            len=1,
            unit_id=1
        )
        point2 = ModbusPoint(
            controller_id=controller.id,
            name="Pressure 1",
            type="input_register",
            data_type="uint16",
            address=30001,
            len=1,
            unit_id=1
        )
        
        test_db_session.add(point1)
        test_db_session.add(point2)
        await test_db_session.commit()
        
        response = await client.get(f"/api/modbus/controllers/{controller.id}/points")
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["total"] == 2
        assert len(data["data"]["points"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_points_by_controller_with_type_filter(self, client: AsyncClient, test_db_session: AsyncSession):
        controller = ModbusController(
            name="Test Controller",
            host="192.168.1.100",
            port=502,
            timeout=10,
            status=True
        )
        test_db_session.add(controller)
        await test_db_session.commit()
        
        point1 = ModbusPoint(
            controller_id=controller.id,
            name="Temperature 1",
            type="holding_register",
            data_type="uint16",
            address=40001,
            len=1,
            unit_id=1
        )
        point2 = ModbusPoint(
            controller_id=controller.id,
            name="Pressure 1",
            type="input_register",
            data_type="uint16",
            address=30001,
            len=1,
            unit_id=1
        )
        
        test_db_session.add(point1)
        test_db_session.add(point2)
        await test_db_session.commit()
        
        response = await client.get(f"/api/modbus/controllers/{controller.id}/points?point_type=holding_register")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 1
        assert data["data"]["points"][0]["type"] == "holding_register"
    
    @pytest.mark.asyncio
    async def test_update_point_success(self, client: AsyncClient, test_db_session: AsyncSession):
        controller = ModbusController(
            name="Test Controller",
            host="192.168.1.100",
            port=502,
            timeout=10,
            status=True
        )
        test_db_session.add(controller)
        await test_db_session.commit()
        
        point = ModbusPoint(
            controller_id=controller.id,
            name="Original Name",
            type="holding_register",
            data_type="uint16",
            address=40001,
            len=1,
            unit_id=1
        )
        test_db_session.add(point)
        await test_db_session.commit()
        
        payload = {
            "name": "Updated Name",
            "description": "Updated description",
            "formula": "x * 0.1",
            "unit": "°C"
        }
        
        response = await client.put(f"/api/modbus/points/{point.id}", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["name"] == "Updated Name"
        assert data["data"]["description"] == "Updated description"
        assert data["data"]["formula"] == "x * 0.1"
        assert data["data"]["unit"] == "°C"
    
    @pytest.mark.asyncio
    async def test_update_point_no_data(self, client: AsyncClient, test_db_session: AsyncSession):
        controller = ModbusController(
            name="Test Controller",
            host="192.168.1.100",
            port=502,
            timeout=10,
            status=True
        )
        test_db_session.add(controller)
        await test_db_session.commit()
        
        point = ModbusPoint(
            controller_id=controller.id,
            name="Test Point",
            type="holding_register",
            data_type="uint16",
            address=40001,
            len=1,
            unit_id=1
        )
        test_db_session.add(point)
        await test_db_session.commit()
        
        payload = {}
        
        response = await client.put(f"/api/modbus/points/{point.id}", json=payload)
        
        assert response.status_code == 400
        data = response.json()
        error_message = data.get("detail") or data.get("message", "")
        assert "No data to update" in error_message
    
    @pytest.mark.asyncio
    async def test_delete_point_success(self, client: AsyncClient, test_db_session: AsyncSession):
        controller = ModbusController(
            name="Test Controller",
            host="192.168.1.100",
            port=502,
            timeout=10,
            status=True
        )
        test_db_session.add(controller)
        await test_db_session.commit()
        
        point = ModbusPoint(
            controller_id=controller.id,
            name="To Delete",
            type="holding_register",
            data_type="uint16",
            address=40001,
            len=1,
            unit_id=1
        )
        test_db_session.add(point)
        await test_db_session.commit()
        
        response = await client.delete(f"/api/modbus/points/{point.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "Point deleted successfully"


class TestModbusDataAPI:
    
    @pytest.mark.asyncio
    async def test_read_controller_points_data_success(self, client: AsyncClient, test_db_session: AsyncSession):
        controller = ModbusController(
            name="Test Controller",
            host="192.168.1.100",
            port=502,
            timeout=10,
            status=True
        )
        test_db_session.add(controller)
        await test_db_session.commit()
        
        point1 = ModbusPoint(
            controller_id=controller.id,
            name="Temperature 1",
            type="holding_register",
            data_type="uint16",
            address=40001,
            len=1,
            unit_id=1,
            formula="x * 0.1",
            unit="°C"
        )
        point2 = ModbusPoint(
            controller_id=controller.id,
            name="Pressure 1",
            type="input_register",
            data_type="uint16",
            address=30001,
            len=1,
            unit_id=1,
            unit="bar"
        )
        
        test_db_session.add(point1)
        test_db_session.add(point2)
        await test_db_session.commit()
        
        response = await client.get(f"/api/modbus/controllers/{controller.id}/points/data")
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["total"] == 2
        assert data["data"]["successful"] == 2
        assert data["data"]["failed"] == 0
        assert len(data["data"]["values"]) == 2
    
    @pytest.mark.asyncio
    async def test_read_controller_points_data_with_type_filter(self, client: AsyncClient, test_db_session: AsyncSession):
        controller = ModbusController(
            name="Test Controller",
            host="192.168.1.100",
            port=502,
            timeout=10,
            status=True
        )
        test_db_session.add(controller)
        await test_db_session.commit()
        
        point1 = ModbusPoint(
            controller_id=controller.id,
            name="Temperature 1",
            type="holding_register",
            data_type="uint16",
            address=40001,
            len=1,
            unit_id=1
        )
        point2 = ModbusPoint(
            controller_id=controller.id,
            name="Pressure 1",
            type="input_register",
            data_type="uint16",
            address=30001,
            len=1,
            unit_id=1
        )
        
        test_db_session.add(point1)
        test_db_session.add(point2)
        await test_db_session.commit()
        
        response = await client.get(f"/api/modbus/controllers/{controller.id}/points/data?point_type=holding_register")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 1
        assert data["data"]["successful"] == 1
    
    @pytest.mark.asyncio
    async def test_write_point_data_success(self, client: AsyncClient, test_db_session: AsyncSession):
        controller = ModbusController(
            name="Test Controller",
            host="192.168.1.100",
            port=502,
            timeout=10,
            status=True
        )
        test_db_session.add(controller)
        await test_db_session.commit()
        
        point = ModbusPoint(
            controller_id=controller.id,
            name="Setpoint 1",
            type="holding_register",
            data_type="uint16",
            address=40001,
            len=1,
            unit_id=1,
            formula="x * 0.1",
            unit="°C"
        )
        test_db_session.add(point)
        await test_db_session.commit()
        
        payload = {
            "value": 75.0,
            "unit_id": 1
        }
        
        response = await client.post(f"/api/modbus/points/{point.id}/write", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["write_value"] == 75.0
        assert data["data"]["success"] is True
        assert data["data"]["point_name"] == "Setpoint 1"
    
    @pytest.mark.asyncio
    async def test_write_point_data_unsupported_type(self, client: AsyncClient, test_db_session: AsyncSession):
        controller = ModbusController(
            name="Test Controller",
            host="192.168.1.100",
            port=502,
            timeout=10,
            status=True
        )
        test_db_session.add(controller)
        await test_db_session.commit()
        
        point = ModbusPoint(
            controller_id=controller.id,
            name="Read Only Point",
            type="input_register",
            data_type="uint16",
            address=30001,
            len=1,
            unit_id=1
        )
        test_db_session.add(point)
        await test_db_session.commit()
        
        payload = {"value": 100}
        
        response = await client.post(f"/api/modbus/points/{point.id}/write", json=payload)
        
        assert response.status_code == 409
        data = response.json()
        error_message = data.get("detail") or data.get("message", "")
        assert "does not support writing" in error_message
    
    @pytest.mark.asyncio
    async def test_write_coil_with_boolean_value(self, client: AsyncClient, test_db_session: AsyncSession):
        controller = ModbusController(
            name="Test Controller",
            host="192.168.1.100",
            port=502,
            timeout=10,
            status=True
        )
        test_db_session.add(controller)
        await test_db_session.commit()
        
        point = ModbusPoint(
            controller_id=controller.id,
            name="Relay 1",
            type="coil",
            data_type="bool",
            address=1,
            len=1,
            unit_id=1
        )
        test_db_session.add(point)
        await test_db_session.commit()
        
        payload = {"value": True}
        
        response = await client.post(f"/api/modbus/points/{point.id}/write", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["write_value"] is True
        assert data["data"]["success"] is True


class TestModbusConfigAPI:
    
    @pytest.mark.asyncio
    async def test_export_controller_config(self, client: AsyncClient, test_db_session: AsyncSession):
        controller = ModbusController(
            name="Test Controller",
            host="192.168.1.100",
            port=502,
            timeout=10,
            status=True
        )
        test_db_session.add(controller)
        await test_db_session.commit()
        
        point = ModbusPoint(
            controller_id=controller.id,
            name="Temperature 1",
            type="holding_register",
            data_type="uint16",
            address=40001,
            len=1,
            unit_id=1,
            formula="x * 0.1",
            unit="°C"
        )
        test_db_session.add(point)
        await test_db_session.commit()
        
        response = await client.get(f"/api/modbus/controllers/{controller.id}/export?format=native")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert "attachment" in response.headers["content-disposition"]
    
    @pytest.mark.asyncio
    async def test_export_controller_config_not_found(self, client: AsyncClient, test_db_session: AsyncSession):
        response = await client.get("/api/modbus/controllers/non-existent-id/export?format=native")
        
        assert response.status_code == 404
        data = response.json()
        error_message = data.get("detail") or data.get("message", "")
        assert "Controller not found" in error_message
    
    @pytest.mark.asyncio
    async def test_import_config_success(self, client: AsyncClient, test_db_session: AsyncSession):
        config_data = {
            "controller": {
                "name": "Imported Controller",
                "host": "192.168.1.200",
                "port": 502,
                "timeout": 10
            },
            "points": [
                {
                    "name": "Imported Point 1",
                    "type": "holding_register",
                    "data_type": "uint16",
                    "address": 40001,
                    "len": 1,
                    "unit_id": 1
                }
            ]
        }
        
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_file_path = f.name
        
        try:
            with open(temp_file_path, 'rb') as f:
                files = {"file": ("config.json", f, "application/json")}
                data = {"format": "native"}
                
                response = await client.post("/api/modbus/config/import", files=files, data=data)
                
                assert response.status_code == 200
                data = response.json()
                assert data["code"] == 200
                assert data["message"] == "Configuration imported successfully"
                assert len(data["data"]["imported_controllers"]) == 1
                assert data["data"]["total_points"] == 1
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_import_config_invalid_file(self, client: AsyncClient, test_db_session: AsyncSession):
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_file_path = f.name
        
        try:
            with open(temp_file_path, 'rb') as f:
                files = {"file": ("config.json", f, "application/json")}
                data = {"format": "native"}
                
                response = await client.post("/api/modbus/config/import", files=files, data=data)
                
                assert response.status_code in [400, 500]
                data = response.json()
                error_message = data.get("detail") or data.get("message", "")
                assert any(keyword in str(error_message).lower() for keyword in ["invalid", "json", "decode", "format", "error"])
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_validate_config_success(self, client: AsyncClient):
        config_data = {
            "controller": {
                "name": "Valid Controller",
                "host": "192.168.1.100",
                "port": 502,
                "timeout": 10
            },
            "points": [
                {
                    "name": "Valid Point",
                    "type": "holding_register",
                    "data_type": "uint16",
                    "address": 40001,
                    "len": 1,
                    "unit_id": 1
                }
            ]
        }
        
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_file_path = f.name
        
        try:
            with open(temp_file_path, 'rb') as f:
                files = {"file": ("config.json", f, "application/json")}
                data = {"format": "native"}
                
                response = await client.post("/api/modbus/config/validate", files=files, data=data)
                
                assert response.status_code == 200
                data = response.json()
                assert data["code"] == 200
                assert data["message"] == "Configuration validation completed"
                assert data["data"]["is_valid"] is True
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_validate_config_invalid_format(self, client: AsyncClient):
        import tempfile
        import os
        
        config_data = {
            "invalid_format": "data"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_file_path = f.name
        
        try:
            with open(temp_file_path, 'rb') as f:
                files = {"file": ("config.json", f, "application/json")}
                data = {"format": "native"}
                
                response = await client.post("/api/modbus/config/validate", files=files, data=data)
                
                assert response.status_code in [200, 422]
                data = response.json()
                if response.status_code == 422:
                    error_message = data.get("detail") or data.get("message", "")
                    assert "Format mismatch" in error_message
                else:
                    assert data["data"]["is_valid"] is False
        finally:
            os.unlink(temp_file_path)


class TestModbusErrorHandling:
    
    @pytest.mark.asyncio
    async def test_invalid_point_type(self, client: AsyncClient, test_db_session: AsyncSession):
        controller = ModbusController(
            name="Test Controller",
            host="192.168.1.100",
            port=502,
            timeout=10,
            status=True
        )
        test_db_session.add(controller)
        await test_db_session.commit()
        
        payload = {
            "controller_id": controller.id,
            "points": [
                {
                    "name": "Invalid Point",
                    "type": "invalid_type",
                    "data_type": "uint16",
                    "address": 40001
                }
            ]
        }
        
        response = await client.post("/api/modbus/points/batch", json=payload)
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_missing_required_fields(self, client: AsyncClient):
        payload = {
            "name": "Test Controller"
        }
        
        response = await client.post("/api/modbus/controllers", json=payload)
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_invalid_port_range(self, test_db_session: AsyncSession):
        mock_modbus = AsyncMock()
        
        def mock_create_tcp(host, port, timeout=30):
            client_id = f"tcp_{host}_{port}"
            mock_client = Mock()
            mock_client.connected = False
            mock_client.is_socket_open.return_value = False
            mock_modbus.clients[client_id] = mock_client
            mock_modbus.client_status[client_id] = False
            return client_id
        
        mock_modbus.create_tcp.side_effect = mock_create_tcp
        
        async def mock_connect(client_id):
            return False
        
        mock_modbus.connect = mock_connect
        mock_modbus.disconnect = Mock(return_value=None)
        mock_modbus.clients = {}
        mock_modbus.client_status = {}
        mock_modbus._initialized = False
        mock_modbus.controller_mapping = {}
        
        from httpx import AsyncClient, ASGITransport
        from main import app
        from core.dependencies import get_db
        
        with patch('extensions.modbus.get_modbus', return_value=mock_modbus), \
             patch('api.modbus.controller.get_modbus', return_value=mock_modbus), \
             patch('api.modbus.services.ModbusManager', return_value=mock_modbus), \
             patch('extensions.modbus.ModbusManager', return_value=mock_modbus):
            
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, 
                base_url="http://testserver",
                timeout=30.0
            ) as ac:
                payload = {
                    "name": "Test Controller",
                    "host": "192.168.1.100",
                    "port": 99999,
                    "timeout": 10
                }
                
                response = await ac.post("/api/modbus/controllers", json=payload)
                
                assert response.status_code == 400
                data = response.json()
                error_message = data.get("detail") or data.get("message", "")
                assert "Connection test failed" in error_message or "Unable to connect" in error_message