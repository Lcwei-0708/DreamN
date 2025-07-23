import pytest
from datetime import datetime
from models.modbus_controller import ModbusController

@pytest.mark.asyncio
async def test_create_modbus_controller(test_db_session):
    """Test creating Modbus controller"""
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
    
    assert controller.id is not None
    assert controller.name == "Test Controller"
    assert controller.host == "192.168.1.100"
    assert controller.port == 502
    assert controller.timeout == 10
    assert controller.status is True
    assert controller.created_at is not None
    assert controller.updated_at is not None

@pytest.mark.asyncio
async def test_read_modbus_controller(test_db_session):
    """Test reading Modbus controller"""
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
    
    # Test query by ID
    result = await test_db_session.get(ModbusController, controller.id)
    assert result is not None
    assert result.name == "Test Controller"
    assert result.host == "192.168.1.100"

@pytest.mark.asyncio
async def test_update_modbus_controller(test_db_session):
    """Test updating Modbus controller"""
    controller = ModbusController(
        name="Original Controller",
        host="192.168.1.100",
        port=502,
        timeout=5,
        status=False
    )
    
    test_db_session.add(controller)
    await test_db_session.commit()
    await test_db_session.refresh(controller)
    
    # Update controller
    controller.name = "Updated Controller"
    controller.host = "192.168.1.200"
    controller.port = 503
    controller.timeout = 15
    controller.status = True
    
    await test_db_session.commit()
    await test_db_session.refresh(controller)
    
    assert controller.name == "Updated Controller"
    assert controller.host == "192.168.1.200"
    assert controller.port == 503
    assert controller.timeout == 15
    assert controller.status is True

@pytest.mark.asyncio
async def test_delete_modbus_controller(test_db_session):
    """Test deleting Modbus controller"""
    controller = ModbusController(
        name="Controller to Delete",
        host="192.168.1.100",
        port=502,
        timeout=10,
        status=True
    )
    
    test_db_session.add(controller)
    await test_db_session.commit()
    await test_db_session.refresh(controller)
    
    controller_id = controller.id
    
    # Delete controller
    await test_db_session.delete(controller)
    await test_db_session.commit()
    
    # Verify deletion
    result = await test_db_session.get(ModbusController, controller_id)
    assert result is None

@pytest.mark.asyncio
async def test_modbus_controller_repr(test_db_session):
    """Test Modbus controller __repr__ method"""
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
    
    repr_str = repr(controller)
    assert "ModbusController" in repr_str
    assert controller.id in repr_str
    assert controller.name in repr_str
    assert controller.host in repr_str
    assert str(controller.port) in repr_str
    assert str(controller.status) in repr_str