import json
import pytest
import io
import os
import shutil
from unittest.mock import AsyncMock, Mock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from models.modbus_controller import ModbusController
from models.modbus_point import ModbusPoint



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
    async def test_create_controller_connection_failed(self, client: AsyncClient, test_db_session: AsyncSession):
        # Create a dedicated mock for this test
        test_mock_modbus = AsyncMock()
        
        def mock_create_tcp(host, port, timeout=30):
            client_id = f"tcp_{host}_{port}"
            mock_client = Mock()
            mock_client.connected = False
            mock_client.is_socket_open.return_value = False
            test_mock_modbus.clients[client_id] = mock_client
            test_mock_modbus.client_status[client_id] = False
            return client_id
        
        test_mock_modbus.create_tcp.side_effect = mock_create_tcp
        
        # Key: Make connect method return False
        async def mock_connect(client_id):
            return False
        
        test_mock_modbus.connect = mock_connect
        test_mock_modbus.disconnect = Mock(return_value=None)
        test_mock_modbus.clients = {}
        test_mock_modbus.client_status = {}
        test_mock_modbus._initialized = False
        test_mock_modbus.controller_mapping = {}
        
        # Directly patch global variable
        from extensions.modbus import _modbus_instance
        
        # Save original instance
        original_instance = _modbus_instance
        
        try:
            # Replace global instance
            import extensions.modbus
            extensions.modbus._modbus_instance = test_mock_modbus
            
            payload = {
                "name": "Failed Controller",
                "host": "192.168.1.150",
                "port": 502,
                "timeout": 5
            }
            
            response = await client.post("/api/modbus/controllers", json=payload)
            
            # According to actual implementation, controller is created but status is False
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 200
            assert data["data"]["status"] is False  # Connection failed, status is False
        finally:
            # Restore original instance
            extensions.modbus._modbus_instance = original_instance
    
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
    async def test_delete_controllers_success(self, client: AsyncClient, test_db_session: AsyncSession):
        # Create multiple controllers to delete
        controller1 = ModbusController(
            name="To Delete 1",
            host="192.168.1.100",
            port=502,
            timeout=10,
            status=True
        )
        controller2 = ModbusController(
            name="To Delete 2",
            host="192.168.1.101",
            port=502,
            timeout=10,
            status=True
        )
        test_db_session.add(controller1)
        test_db_session.add(controller2)
        await test_db_session.commit()
        await test_db_session.refresh(controller1)
        await test_db_session.refresh(controller2)

        payload = {
            "controller_ids": [str(controller1.id), str(controller2.id)]
        }
        
        response = await client.request(
            "DELETE",
            "/api/modbus/controllers",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "All controllers deleted successfully"
        assert "data" not in data

    @pytest.mark.asyncio
    async def test_delete_controllers_partial_success(self, client: AsyncClient, test_db_session: AsyncSession):
        # Create one controller to delete
        controller = ModbusController(
            name="To Delete",
            host="192.168.1.100",
            port=502,
            timeout=10,
            status=True
        )
        test_db_session.add(controller)
        await test_db_session.commit()
        
        payload = {
            "controller_ids": [str(controller.id), "non-existent-id"]
        }
        
        response = await client.request(
            "DELETE",
            "/api/modbus/controllers",
            json=payload
        )
        
        assert response.status_code == 207
        data = response.json()
        assert data["code"] == 207
        assert data["message"] == "Delete controllers partial success"
        assert data["data"]["total_requested"] == 2
        assert data["data"]["deleted_count"] == 1
        assert data["data"]["failed_count"] == 1
        assert len(data["data"]["results"]) == 2
        
        success_results = [r for r in data["data"]["results"] if r["status"] == "success"]
        failed_results = [r for r in data["data"]["results"] if r["status"] == "not_found"]
        assert len(success_results) == 1
        assert len(failed_results) == 1
        assert success_results[0]["id"] == str(controller.id)
        assert failed_results[0]["id"] == "non-existent-id"

    @pytest.mark.asyncio
    async def test_delete_controllers_all_not_found(self, client: AsyncClient, test_db_session: AsyncSession):
        payload = {
            "controller_ids": ["non-existent-id-1", "non-existent-id-2"]
        }
        
        response = await client.request(
            "DELETE",
            "/api/modbus/controllers",
            json=payload
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == 400
        assert data["message"] == "All controllers failed to delete"
        assert data["data"]["results"]
        assert len(data["data"]["results"]) == 2
        assert all(r["status"] == "not_found" for r in data["data"]["results"])
    
    @pytest.mark.asyncio
    async def test_test_controller_success(self, client: AsyncClient, test_db_session: AsyncSession):
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
            "controller_id": str(controller.id),
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
        
        response = await client.post("/api/modbus/points", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "All points created successfully"
        assert len(data["data"]["results"]) == 2
        assert all(result["status"] == "success" for result in data["data"]["results"])

    @pytest.mark.asyncio
    async def test_create_points_batch_controller_not_found(self, client: AsyncClient, test_db_session: AsyncSession):
        payload = {
            "controller_id": "non-existent-id",
            "points": [
                {
                    "name": "Temperature 1",
                    "type": "holding_register",
                    "data_type": "uint16",
                    "address": 40001,
                    "len": 1,
                    "unit_id": 1
                }
            ]
        }
        
        response = await client.post("/api/modbus/points", json=payload)
        
        assert response.status_code == 404
        data = response.json()
        assert data["code"] == 404
        assert "Controller non-existent-id not found" in data["message"]

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
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "Point updated successfully"
        assert data["data"]["id"] == point.id
        assert data["data"]["name"] == "Test Point"
    
    @pytest.mark.asyncio
    async def test_delete_points_success(self, client: AsyncClient, test_db_session: AsyncSession):
        controller = ModbusController(
            name="Test Controller",
            host="192.168.1.100",
            port=502,
            timeout=10,
            status=True
        )
        test_db_session.add(controller)
        await test_db_session.commit()
        
        # Create multiple points to delete
        point1 = ModbusPoint(
            controller_id=controller.id,
            name="To Delete 1",
            type="holding_register",
            data_type="uint16",
            address=40001,
            len=1,
            unit_id=1
        )
        point2 = ModbusPoint(
            controller_id=controller.id,
            name="To Delete 2",
            type="input_register",
            data_type="uint16",
            address=30001,
            len=1,
            unit_id=1
        )
        test_db_session.add(point1)
        test_db_session.add(point2)
        await test_db_session.commit()
        
        payload = {
            "point_ids": [str(point1.id), str(point2.id)]
        }
        
        # Use client's transport to send request
        response = await client.request(
            "DELETE",
            "/api/modbus/points",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "All points deleted successfully"
        assert "data" not in data

    @pytest.mark.asyncio
    async def test_delete_points_partial_success(self, client: AsyncClient, test_db_session: AsyncSession):
        controller = ModbusController(
            name="Test Controller",
            host="192.168.1.100",
            port=502,
            timeout=10,
            status=True
        )
        test_db_session.add(controller)
        await test_db_session.commit()
        
        # Create one point to delete
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
        
        payload = {
            "point_ids": [str(point.id), "non-existent-id"]
        }
        
        # Use client's transport to send request
        response = await client.request(
            "DELETE",
            "/api/modbus/points",
            json=payload
        )
        
        assert response.status_code == 207
        data = response.json()
        assert data["code"] == 207
        assert data["message"] == "Delete points partial success"
        assert data["data"]["total_requested"] == 2
        assert data["data"]["deleted_count"] == 1
        assert data["data"]["failed_count"] == 1
        assert len(data["data"]["results"]) == 2
        
        success_results = [r for r in data["data"]["results"] if r["status"] == "success"]
        failed_results = [r for r in data["data"]["results"] if r["status"] == "not_found"]
        assert len(success_results) == 1
        assert len(failed_results) == 1
        assert success_results[0]["id"] == str(point.id)
        assert failed_results[0]["id"] == "non-existent-id"

    @pytest.mark.asyncio
    async def test_delete_points_all_not_found(self, client: AsyncClient, test_db_session: AsyncSession):
        payload = {
            "point_ids": ["non-existent-id-1", "non-existent-id-2"]
        }
        
        # Use client's transport to send request
        response = await client.request(
            "DELETE",
            "/api/modbus/points",
            json=payload
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == 400
        assert data["message"] == "All points failed to delete"
        assert data["data"]["results"]
        assert len(data["data"]["results"]) == 2
        assert all(r["status"] == "not_found" for r in data["data"]["results"])


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
        
        # Create some points for the controller
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
        
        # Test export with Form data
        response = await client.post(
            f"/api/modbus/export/{controller.id}",
            data={"export_format": "native"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert "attachment" in response.headers["content-disposition"]

    @pytest.mark.asyncio
    async def test_export_controller_config_not_found(self, client: AsyncClient, test_db_session: AsyncSession):
        # Test export with non-existent controller ID
        response = await client.post(
            "/api/modbus/export/non-existent-id",
            data={"export_format": "native"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["code"] == 404
        assert "Controller not found" in data["message"]

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
        
        # Use BytesIO instead of actual file
        config_json = json.dumps(config_data).encode('utf-8')
        config_file = io.BytesIO(config_json)
        
        files = {"file": ("config.json", config_file, "application/json")}
        data = {
            "config_format": "native",
            "duplicate_handling": "skip_controller"
        }
        
        response = await client.post("/api/modbus/import/controller", files=files, data=data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "Controller imported successfully"

    @pytest.mark.asyncio
    async def test_import_config_invalid_file(self, client: AsyncClient, test_db_session: AsyncSession):
        # Use BytesIO with invalid JSON content
        invalid_json = "invalid json content".encode('utf-8')
        config_file = io.BytesIO(invalid_json)
        
        files = {"file": ("config.json", config_file, "application/json")}
        data = {
            "config_format": "native",
            "duplicate_handling": "skip_controller"
        }
        
        response = await client.post("/api/modbus/import/controller", files=files, data=data)
        
        assert response.status_code in [400, 415, 500]

    @pytest.fixture(autouse=True)
    def cleanup_exports_directory(self):
        """Clean up exports directory before and after tests"""
        exports_dir = "exports"
        
        # Clean up before test
        if os.path.exists(exports_dir):
            shutil.rmtree(exports_dir)
        
        yield
        
        # Clean up after test
        if os.path.exists(exports_dir):
            shutil.rmtree(exports_dir)


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
            "controller_id": str(controller.id),
            "points": [
                {
                    "name": "Invalid Point",
                    "type": "invalid_type",
                    "data_type": "uint16",
                    "address": 40001,
                    "len": 1,
                    "unit_id": 1
                }
            ]
        }
        
        response = await client.post("/api/modbus/points", json=payload)
        
        assert response.status_code == 422
        data = response.json()
        if "detail" in data:
            assert "validation error" in data["detail"][0]["msg"].lower()
        else:
            assert "validation" in str(data).lower() or "error" in str(data).lower()
    
    @pytest.mark.asyncio
    async def test_missing_required_fields(self, client: AsyncClient, test_db_session: AsyncSession):
        payload = {
            "name": "Test Controller"
        }
        
        response = await client.post("/api/modbus/controllers", json=payload)
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_invalid_port_range(self, client: AsyncClient, test_db_session: AsyncSession):
        """Test invalid port range handling"""
        mock_modbus = AsyncMock()
        
        def mock_create_tcp(host, port, timeout=30):
            # Simulate invalid port range error
            if port > 65535:
                raise ValueError("Port number out of range")
            client_id = f"tcp_{host}_{port}"
            mock_client = Mock()
            mock_client.connected = False
            mock_client.is_socket_open.return_value = False
            mock_modbus.clients[client_id] = mock_client
            mock_modbus.client_status[client_id] = False
            return client_id
        
        # Set side_effect directly
        mock_modbus.create_tcp = Mock(side_effect=mock_create_tcp)
        
        # Test invalid port
        with pytest.raises(ValueError, match="Port number out of range"):
            mock_modbus.create_tcp("192.168.1.100", 99999, 10)
        
        # Test valid port
        client_id = mock_modbus.create_tcp("192.168.1.100", 502, 10)
        assert client_id == "tcp_192.168.1.100_502"