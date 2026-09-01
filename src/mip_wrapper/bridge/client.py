"""Bridge client: Python process management of .NET helper."""

import json
import logging
import queue
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from mip_wrapper.exceptions import NativeRuntimeError, ProtocolError
from mip_wrapper.bridge.protocol import (
    DecryptResult,
    InspectResult,
    ProtocolRequest,
    ProtocolResponse,
)
from mip_wrapper.version import check_helper_version, check_protocol_version

logger = logging.getLogger(__name__)


class HelperClient:
    """Manages the .NET MipWrapper.Helper process."""

    def __init__(self, helper_path: Path, timeout_seconds: int = 120) -> None:
        """
        Initialize helper client.

        Args:
            helper_path: Path to MipWrapper.Helper executable
            timeout_seconds: Process timeout for operations
        """
        self.helper_path = helper_path
        self.timeout_seconds = timeout_seconds
        self._process: subprocess.Popen[str] | None = None
        self._stdout_queue: queue.Queue[str | None] | None = None
        logger.debug(f"HelperClient initialized: {helper_path}")

    def _read_stdout(self, process: subprocess.Popen[str], output: queue.Queue[str | None]) -> None:
        if process.stdout is None:
            output.put(None)
            return
        try:
            for line in iter(process.stdout.readline, ""):
                if not isinstance(line, str):
                    break
                output.put(line)
        finally:
            output.put(None)

    def _drain_stderr(self, process: subprocess.Popen[str]) -> None:
        if process.stderr is None:
            return
        for line in iter(process.stderr.readline, ""):
            if not isinstance(line, str):
                break
            sys.stderr.write(line)
            sys.stderr.flush()

    def _spawn_helper(self) -> subprocess.Popen[str]:
        """Spawn helper process if not already running."""
        if self._process is not None:
            return self._process

        try:
            self._process = subprocess.Popen(
                [str(self.helper_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            self._stdout_queue = queue.Queue()
            threading.Thread(target=self._read_stdout, args=(self._process, self._stdout_queue), daemon=True).start()
            threading.Thread(target=self._drain_stderr, args=(self._process,), daemon=True).start()
            logger.debug("Helper process spawned")
        except FileNotFoundError as e:
            raise NativeRuntimeError(
                f"Helper executable not found: {self.helper_path}",
                error_code="HelperNotFound",
            ) from e
        except Exception as e:
            raise NativeRuntimeError(
                f"Failed to spawn helper: {e}",
                error_code="HelperSpawnFailed",
            ) from e

        return self._process

    def _terminate_helper(self) -> None:
        process = self._process
        self._process = None
        self._stdout_queue = None
        if process is None:
            return

        try:
            try:
                process.terminate()
            except Exception:
                pass

            try:
                process.wait(timeout=2)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
                try:
                    process.wait(timeout=2)
                except Exception:
                    pass
        finally:
            for pipe in (process.stdin, process.stdout, process.stderr):
                if pipe is not None:
                    try:
                        pipe.close()
                    except Exception:
                        pass

    def _send_request(self, request: ProtocolRequest) -> ProtocolResponse:
        """Send request to helper and get response."""
        process = self._spawn_helper()

        if process.stdin is None or process.stdout is None:
            raise NativeRuntimeError(
                "Helper process pipes are not available",
                error_code="HelperPipeFailed",
            )

        try:
            request_json = request.to_json()
            logger.debug(f"Sending request: {request.command}")
            process.stdin.write(request_json + "\n")
            process.stdin.flush()

            if self._stdout_queue is None:
                raise NativeRuntimeError(
                    "Helper stdout reader is not available",
                    error_code="HelperPipeFailed",
                )

            try:
                response_json = self._stdout_queue.get(
                    timeout=request.timeout_seconds or self.timeout_seconds
                )
            except queue.Empty as error:
                self._terminate_helper()
                raise NativeRuntimeError(
                    f"Helper operation timed out: {request.command}",
                    error_code="HelperTimeout",
                ) from error

            if response_json is None:
                self._terminate_helper()
                raise ProtocolError(
                    f"Helper exited before responding to {request.command}",
                    error_code="HelperTerminated",
                )

            if not response_json:
                raise ProtocolError(
                    "Helper process terminated without response",
                    error_code="HelperTerminated",
                )

            logger.debug("Received response from helper")
            response = ProtocolResponse.from_json(response_json)

            # Validate protocol version
            try:
                check_protocol_version(response.protocol_version)
            except ValueError as e:
                raise ProtocolError(str(e), error_code="ProtocolVersionMismatch") from e

            return response

        except (BrokenPipeError, OSError) as e:
            raise ProtocolError(
                f"Communication with helper failed: {e}",
                error_code="ProtocolFailed",
            ) from e

    def inspect(
        self,
        tenant_id: str,
        client_id: str,
        certificate_path: str,
        authorization_mode: str,
        delegated_user: str | None,
        source_path: str,
        timeout_seconds: int | None = None,
        client_secret: str | None = None,
    ) -> InspectResult:
        """
        Inspect file protection metadata.

        Returns:
            InspectResult with file metadata
        """
        request = ProtocolRequest(
            command="inspect",
            tenant_id=tenant_id,
            client_id=client_id,
            certificate_path=certificate_path,
            authorization_mode=authorization_mode,
            delegated_user=delegated_user,
            source_path=source_path,
            timeout_seconds=timeout_seconds or self.timeout_seconds,
            client_secret=client_secret,
        )

        response = self._send_request(request)
        data = response.ensure_success()
        return InspectResult.from_response(data)

    def decrypt(
        self,
        tenant_id: str,
        client_id: str,
        certificate_path: str,
        authorization_mode: str,
        delegated_user: str | None,
        source_path: str,
        output_path: str,
        timeout_seconds: int | None = None,
        client_secret: str | None = None,
    ) -> DecryptResult:
        """
        Decrypt file to output path.

        Returns:
            DecryptResult with output path and size
        """
        request = ProtocolRequest(
            command="decrypt",
            tenant_id=tenant_id,
            client_id=client_id,
            certificate_path=certificate_path,
            authorization_mode=authorization_mode,
            delegated_user=delegated_user,
            source_path=source_path,
            output_path=output_path,
            timeout_seconds=timeout_seconds or self.timeout_seconds,
            client_secret=client_secret,
        )

        response = self._send_request(request)
        data = response.ensure_success()
        return DecryptResult.from_response(data)

    def shutdown(self) -> None:
        """Shutdown helper process gracefully."""
        if self._process is None:
            return

        try:
            request = ProtocolRequest(command="shutdown")
            self._send_request(request)
        except Exception as e:
            logger.warning(f"Shutdown request failed: {e}")
        finally:
            self._terminate_helper()

    def __del__(self) -> None:
        """Cleanup on deletion."""
        self.shutdown()
