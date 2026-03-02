"""Unit tests for fetch_target notification safety guards."""

from types import SimpleNamespace

from importer.web.pages import fetch_target


def test_safe_notify_skips_deleted_client(monkeypatch) -> None:
    calls: list[tuple[str, str, object]] = []

    def fake_notify(message: str, *, type: str, timeout=None) -> None:
        calls.append((message, type, timeout))

    fake_ui = SimpleNamespace(
        context=SimpleNamespace(client=SimpleNamespace(_deleted=True, has_socket_connection=True)),
        notify=fake_notify,
    )
    monkeypatch.setattr(fetch_target, "ui", fake_ui)

    ok = fetch_target._safe_notify("x", notify_type="warning")

    assert ok is False
    assert calls == []


def test_safe_notify_skips_disconnected_client(monkeypatch) -> None:
    calls: list[tuple[str, str, object]] = []

    def fake_notify(message: str, *, type: str, timeout=None) -> None:
        calls.append((message, type, timeout))

    fake_ui = SimpleNamespace(
        context=SimpleNamespace(client=SimpleNamespace(_deleted=False, has_socket_connection=False)),
        notify=fake_notify,
    )
    monkeypatch.setattr(fetch_target, "ui", fake_ui)

    ok = fetch_target._safe_notify("x", notify_type="negative", timeout=10)

    assert ok is False
    assert calls == []


def test_safe_notify_calls_notify_for_active_client(monkeypatch) -> None:
    calls: list[tuple[str, str, object]] = []

    def fake_notify(message: str, *, type: str, timeout=None) -> None:
        calls.append((message, type, timeout))

    fake_ui = SimpleNamespace(
        context=SimpleNamespace(client=SimpleNamespace(_deleted=False, has_socket_connection=True)),
        notify=fake_notify,
    )
    monkeypatch.setattr(fetch_target, "ui", fake_ui)

    ok = fetch_target._safe_notify("hello", notify_type="positive", timeout=5)

    assert ok is True
    assert calls == [("hello", "positive", 5)]
