import pytest
from sqlalchemy.exc import IntegrityError
from models.webpush_subscription import WebPushSubscription

@pytest.mark.asyncio
async def test_create_and_query_webpush_subscription(test_db_session):
    sub = WebPushSubscription(
        user_id="user-123",
        endpoint="https://example.com/endpoint/abc",
        keys={"p256dh": "key1", "auth": "key2"},
        is_active=True,
        user_agent="Mozilla/5.0"
    )
    test_db_session.add(sub)
    await test_db_session.commit()
    await test_db_session.refresh(sub)

    assert sub.id is not None
    assert sub.user_id == "user-123"
    assert sub.endpoint == "https://example.com/endpoint/abc"
    assert sub.keys == {"p256dh": "key1", "auth": "key2"}
    assert sub.is_active is True
    assert sub.user_agent == "Mozilla/5.0"
    assert sub.created_at is not None
    assert sub.updated_at is not None

    result = await test_db_session.get(WebPushSubscription, sub.id)
    assert result is not None
    assert result.endpoint == "https://example.com/endpoint/abc"
    assert result.user_id == "user-123"

@pytest.mark.asyncio
async def test_webpush_subscription_unique_endpoint(test_db_session):
    sub1 = WebPushSubscription(
        user_id="user-1",
        endpoint="https://example.com/endpoint/unique",
        keys={"p256dh": "k1", "auth": "k2"},
        is_active=True,
        user_agent="UA"
    )
    test_db_session.add(sub1)
    await test_db_session.commit()

    sub2 = WebPushSubscription(
        user_id="user-2",
        endpoint="https://example.com/endpoint/unique",
        keys={"p256dh": "k3", "auth": "k4"},
        is_active=True,
        user_agent="UA"
    )
    test_db_session.add(sub2)
    with pytest.raises(IntegrityError):
        await test_db_session.commit()
        await test_db_session.rollback()