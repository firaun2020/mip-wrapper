"""Bridge client: Python process management of .NET helper."""

import json
import logging
import subprocess
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

    def __init__(self, helper_path: Path, timeout_seconds: int = 30) -> None:
        """
        Initialize helper client.

        Args:
            helper_path: Path to MipWrapper.Helper executable
            timeout_seconds: Process timeout for operations
        """
        self.helper_path = helper_path
        self.timeout_seconds = timeout_seconds
        self._process: subprocess.Popen[str] | None = None
        logger.debug(f"HelperClient initialized: {helper_path}")

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

            response_json = process.stdout.readline()
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
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None

    def __del__(self) -> None:
        """Cleanup on deletion."""
        self.shutdown()
