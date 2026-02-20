"""Tests for Terraform import stream cleanup behavior."""

import asyncio

from importer.web.utils import terraform_import


class _FakeStdout:
    def __init__(self, lines: list[bytes]) -> None:
        self._lines = lines
        self._index = 0
        self.closed = False

    def __aiter__(self) -> "_FakeStdout":
        return self

    async def __anext__(self) -> bytes:
        if self._index >= len(self._lines):
            raise StopAsyncIteration
        value = self._lines[self._index]
        self._index += 1
        return value

    async def aclose(self) -> None:
        self.closed = True


class _FakeProcess:
    def __init__(self, stdout: _FakeStdout) -> None:
        self.stdout = stdout
        self.returncode = 0
        self.wait_called = False

    async def wait(self) -> int:
        self.wait_called = True
        return self.returncode


def test_run_terraform_import_closes_stdout_stream(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_stdout = _FakeStdout([b"line-1\n", b"line-2\n"])
    fake_process = _FakeProcess(fake_stdout)

    async def _fake_create_subprocess_exec(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return fake_process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _fake_create_subprocess_exec)

    success, output = asyncio.run(
        terraform_import.run_terraform_import(
            "module.dbt_cloud.fake",
            "123",
            ".",
        )
    )

    assert success is True
    assert "line-1" in output and "line-2" in output
    assert fake_process.wait_called is True
    assert fake_stdout.closed is True
