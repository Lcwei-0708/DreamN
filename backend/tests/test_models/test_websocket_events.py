import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from models.websocket_events import WebSocketEvents

@pytest.mark.asyncio
async def test_create_and_query_websocket_events(test_db_session):
    sub = WebSocketEvents(
        user_id="user-123",
        event_type="connect",
        event_time=datetime.now(),
        ip_address="127.0.0.1"
    )
    test_db_session.add(sub)
    await test_db_session.commit()
    await test_db_session.refresh(sub)

    assert sub.id is not None
    assert sub.user_id == "user-123"
    assert sub.event_type == "connect"
    assert sub.event_time is not None
    assert sub.ip_address == "127.0.0.1"

    result = await test_db_session.get(WebSocketEvents, sub.id)
    assert result is not None
    assert result.user_id == "user-123"
    assert result.event_type == "connect"
    assert result.event_time is not None
    assert result.ip_address == "127.0.0.1"