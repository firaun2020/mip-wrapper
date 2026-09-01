"""Tests for helper process lifecycle and bounded protocol I/O."""

import io
import subprocess
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mip_wrapper.bridge.client import HelperClient
from mip_wrapper.bridge.protocol import ProtocolRequest
from mip_wrapper.exceptions import NativeRuntimeError, ProtocolError


class BlockingPipe:
    def __init__(self) -> None:
        self.released = threading.Event()

    def readline(self) -> str:
        self.released.wait()
        return ""

    def close(self) -> None:
        self.released.set()


def process(stdout, stderr=""):
    value = MagicMock()
    value.stdin = io.StringIO()
    value.stdout = stdout
    value.stderr = io.StringIO(stderr)
    value.terminate.side_effect = lambda: getattr(stdout, "close", lambda: None)()
    value.kill.side_effect = lambda: getattr(stdout, "close", lambda: None)()
    value.wait.return_value = 0
    return value


def request() -> ProtocolRequest:
    return ProtocolRequest(command="inspect", timeout_seconds=0.01)


def test_helper_never_responds_times_out_and_is_terminated():
    stdout = BlockingPipe()
    helper_process = process(stdout)
    client = HelperClient(Path("fake-helper"), timeout_seconds=0.01)

    with patch("mip_wrapper.bridge.client.subprocess.Popen", return_value=helper_process):
        with pytest.raises(NativeRuntimeError, match="timed out: inspect"):
            client._send_request(request())

    helper_process.terminate.assert_called_once()
    helper_process.stdin.close()
    helper_process.stderr.close()


def test_substantial_stderr_is_drained_without_blocking_response(capsys):
    helper_process = process(
        io.StringIO('{"protocol_version":"1.0","request_id":"x","success":true,"result":{}}\n'),
        stderr="diagnostic\n" * 10000,
    )
    client = HelperClient(Path("fake-helper"), timeout_seconds=1)

    with patch("mip_wrapper.bridge.client.subprocess.Popen", return_value=helper_process):
        response = client._send_request(request())

    assert response.success is True
    assert "diagnostic" in capsys.readouterr().err


def test_helper_exit_before_response_is_reported():
    helper_process = process(io.StringIO(""))
    client = HelperClient(Path("fake-helper"), timeout_seconds=1)

    with patch("mip_wrapper.bridge.client.subprocess.Popen", return_value=helper_process):
        with pytest.raises(ProtocolError, match="exited before responding"):
            client._send_request(request())


def test_timeout_kills_helper_when_termination_does_not_finish():
    stdout = BlockingPipe()
    helper_process = process(stdout)
    helper_process.wait.side_effect = [subprocess.TimeoutExpired("fake-helper", 2), 0]
    client = HelperClient(Path("fake-helper"), timeout_seconds=0.01)

    with patch("mip_wrapper.bridge.client.subprocess.Popen", return_value=helper_process):
        with pytest.raises(NativeRuntimeError, match="timed out"):
            client._send_request(request())

    helper_process.kill.assert_called_once()


def test_normal_response_still_succeeds():
    helper_process = process(
        io.StringIO('{"protocol_version":"1.0","request_id":"x","success":true,"result":{}}\n')
    )
    client = HelperClient(Path("fake-helper"), timeout_seconds=1)

    with patch("mip_wrapper.bridge.client.subprocess.Popen", return_value=helper_process):
        response = client._send_request(request())

    assert response.success is True
