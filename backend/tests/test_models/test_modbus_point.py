import pytest
from datetime import datetime
from models.modbus_point import ModbusPoint
from models.modbus_controller import ModbusController

@pytest.mark.asyncio
async def test_create_modbus_point(test_db_session):
    """Test creating Modbus point"""
    # Create controller first
    controller = ModbusController(
        name="Test Controller",
        host="192.168.1.100",
        port=502,
        timeout=10,
        status=True
    )
    test_db_session.add(controller)
    await test_db_session.commit()
    await test_db_session.refresh(controller)
    
    # Create point
    point = ModbusPoint(
        controller_id=controller.id,
        name="Temperature Sensor",
        description="Boiler temperature sensor",
        type="holding_register",
        data_type="uint16",
        address=40001,
        len=1,
        unit_id=1,
        formula="x * 0.1",
        unit="°C",
        min_value=0.0,
        max_value=100.0
    )
    
    test_db_session.add(point)
    await test_db_session.commit()
    await test_db_session.refresh(point)
    
    assert point.id is not None
    assert point.controller_id == controller.id
    assert point.name == "Temperature Sensor"
    assert point.description == "Boiler temperature sensor"
    assert point.type == "holding_register"
    assert point.data_type == "uint16"
    assert point.address == 40001
    assert point.len == 1
    assert point.unit_id == 1
    assert point.formula == "x * 0.1"
    assert point.unit == "°C"
    assert point.min_value == 0.0
    assert point.max_value == 100.0
    assert point.created_at is not None
    assert point.updated_at is not None

@pytest.mark.asyncio
async def test_read_modbus_point(test_db_session):
    """Test reading Modbus point"""
    # Create controller first
    controller = ModbusController(
        name="Test Controller",
        host="192.168.1.100",
        port=502,
        timeout=10,
        status=True
    )
    test_db_session.add(controller)
    await test_db_session.commit()
    await test_db_session.refresh(controller)
    
    # Create point
    point = ModbusPoint(
        controller_id=controller.id,
        name="Temperature Sensor",
        type="holding_register",
        data_type="uint16",
        address=40001,
        len=1,
        unit_id=1
    )
    
    test_db_session.add(point)
    await test_db_session.commit()
    await test_db_session.refresh(point)
    
    # Test query by ID
    result = await test_db_session.get(ModbusPoint, point.id)
    assert result is not None
    assert result.name == "Temperature Sensor"
    assert result.controller_id == controller.id

@pytest.mark.asyncio
async def test_update_modbus_point(test_db_session):
    """Test updating Modbus point"""
    # Create controller first
    controller = ModbusController(
        name="Test Controller",
        host="192.168.1.100",
        port=502,
        timeout=10,
        status=True
    )
    test_db_session.add(controller)
    await test_db_session.commit()
    await test_db_session.refresh(controller)
    
    # Create point
    point = ModbusPoint(
        controller_id=controller.id,
        name="Original Point",
        type="holding_register",
        data_type="uint16",
        address=40001,
        len=1,
        unit_id=1
    )
    
    test_db_session.add(point)
    await test_db_session.commit()
    await test_db_session.refresh(point)
    
    # Update point
    point.name = "Updated Point"
    point.description = "Updated description"
    point.formula = "x * 2.0"
    point.unit = "bar"
    point.min_value = 10.0
    point.max_value = 200.0
    
    await test_db_session.commit()
    await test_db_session.refresh(point)
    
    assert point.name == "Updated Point"
    assert point.description == "Updated description"
    assert point.formula == "x * 2.0"
    assert point.unit == "bar"
    assert point.min_value == 10.0
    assert point.max_value == 200.0

@pytest.mark.asyncio
async def test_delete_modbus_point(test_db_session):
    """Test deleting Modbus point"""
    # Create controller first
    controller = ModbusController(
        name="Test Controller",
        host="192.168.1.100",
        port=502,
        timeout=10,
        status=True
    )
    test_db_session.add(controller)
    await test_db_session.commit()
    await test_db_session.refresh(controller)
    
    # Create point
    point = ModbusPoint(
        controller_id=controller.id,
        name="Point to Delete",
        type="holding_register",
        data_type="uint16",
        address=40001,
        len=1,
        unit_id=1
    )
    
    test_db_session.add(point)
    await test_db_session.commit()
    await test_db_session.refresh(point)
    
    point_id = point.id
    
    # Delete point
    await test_db_session.delete(point)
    await test_db_session.commit()
    
    # Verify deletion
    result = await test_db_session.get(ModbusPoint, point_id)
    assert result is None

@pytest.mark.asyncio
async def test_modbus_point_repr(test_db_session):
    """Test Modbus point __repr__ method"""
    # Create controller first
    controller = ModbusController(
        name="Test Controller",
        host="192.168.1.100",
        port=502,
        timeout=10,
        status=True
    )
    test_db_session.add(controller)
    await test_db_session.commit()
    await test_db_session.refresh(controller)
    
    # Create point
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
    await test_db_session.refresh(point)
    
    repr_str = repr(point)
    assert "ModbusPoint" in repr_str
    assert point.id in repr_str
    assert point.name in repr_str
    assert point.type in repr_str
    assert str(point.address) in repr_str
    assert str(point.unit_id) in repr_str

@pytest.mark.asyncio
async def test_modbus_point_foreign_key_constraint(test_db_session):
    """Test Modbus point foreign key constraint"""
    point = ModbusPoint(
        controller_id="non-existent-controller-id",
        name="Test Point",
        type="holding_register",
        data_type="uint16",
        address=0,
        len=1,
        unit_id=1
    )
    
    test_db_session.add(point)
    
    with pytest.raises(Exception):
        await test_db_session.commit()
        await test_db_session.rollback()