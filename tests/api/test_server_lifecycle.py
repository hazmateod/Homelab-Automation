import asyncio

from himp.api import server


def test_application_lifespan_closes_postgresql_pools(monkeypatch):
    calls = []

    def fake_close_pools():
        calls.append("close_pools")

    monkeypatch.setattr(
        server.PostgreSQLDatabase,
        "close_pools",
        fake_close_pools,
    )

    async def exercise_lifespan():
        async with server.application_lifespan(None):
            assert calls == []

    asyncio.run(exercise_lifespan())

    assert calls == ["close_pools"]
