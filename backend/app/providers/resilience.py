"""Bounded provider timeout, retry, and circuit-breaker primitives."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Awaitable, Callable, TypeVar


class ProviderErrorCode(StrEnum):
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    CIRCUIT_OPEN = "circuit_open"


class ProviderExecutionError(Exception):
    """Safe error metadata used by the gateway; raw upstream details stay internal."""

    def __init__(self, code: ProviderErrorCode, *, retryable: bool = True):
        self.code = code
        self.retryable = retryable
        super().__init__(code.value)


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    cooldown_seconds: float = 30.0
    clock: Callable[[], float] = time.monotonic
    state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    opened_at: float | None = None
    _probe_in_flight: bool = field(default=False, init=False, repr=False)

    def before_call(self) -> None:
        now = self.clock()
        if self.state is CircuitState.OPEN:
            if self.opened_at is None or now - self.opened_at < self.cooldown_seconds:
                raise ProviderExecutionError(ProviderErrorCode.CIRCUIT_OPEN)
            self.state = CircuitState.HALF_OPEN
            self._probe_in_flight = False

        if self.state is CircuitState.HALF_OPEN:
            if self._probe_in_flight:
                raise ProviderExecutionError(ProviderErrorCode.CIRCUIT_OPEN)
            self._probe_in_flight = True

    def record_success(self) -> None:
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.opened_at = None
        self._probe_in_flight = False

    def record_failure(self) -> None:
        self._probe_in_flight = False
        if self.state is CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.opened_at = self.clock()
            return
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = self.clock()


T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    timeout_seconds: float = 20.0
    max_retries: int = 1
    backoff_seconds: float = 0.25

    @property
    def max_attempts(self) -> int:
        return self.max_retries + 1


class ProviderExecutor:
    """Execute one adapter operation with bounded retries and a per-domain breaker."""

    def __init__(
        self,
        *,
        policy: RetryPolicy | None = None,
        circuit: CircuitBreaker | None = None,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.policy = policy or RetryPolicy()
        self.circuit = circuit or CircuitBreaker()
        self._sleeper = sleeper

    async def execute(self, operation: Callable[[], Awaitable[T]]) -> T:
        self.circuit.before_call()
        for attempt in range(self.policy.max_attempts):
            try:
                result = await asyncio.wait_for(operation(), timeout=self.policy.timeout_seconds)
                self.circuit.record_success()
                return result
            except ProviderExecutionError as error:
                failure = error
            except asyncio.TimeoutError:
                failure = ProviderExecutionError(ProviderErrorCode.TIMEOUT)
            except Exception:  # noqa: BLE001 - provider boundary must fail closed
                failure = ProviderExecutionError(ProviderErrorCode.UNAVAILABLE)

            if not failure.retryable or attempt >= self.policy.max_retries:
                self.circuit.record_failure()
                raise failure
            delay = self.policy.backoff_seconds * (2**attempt)
            if delay:
                await self._sleeper(delay)

        self.circuit.record_failure()
        raise ProviderExecutionError(ProviderErrorCode.UNAVAILABLE)
