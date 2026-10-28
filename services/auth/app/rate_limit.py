"""Small in-process rate limiter for credential endpoints."""

from collections import OrderedDict, deque
from collections.abc import Collection
from threading import Lock
from time import monotonic

from fastapi import Request

from app.config import TRUSTED_PROXY_IPS
from app.errors import api_error

_SWEEP_INTERVAL = 256
_MAX_TRACKED_IPS = 10_000


class IpRateLimiter:
    """Limit requests by client IP over a rolling time window."""

    def __init__(
        self,
        limit: int = 5,
        window_seconds: float = 60,
        trusted_proxy_ips: Collection[str] = TRUSTED_PROXY_IPS,
        max_tracked_ips: int = _MAX_TRACKED_IPS,
    ) -> None:
        if limit < 1 or window_seconds <= 0 or max_tracked_ips < 1:
            raise ValueError("Rate limiter bounds must be positive")
        self.limit = limit
        self.window_seconds = window_seconds
        self.trusted_proxy_ips = frozenset(trusted_proxy_ips)
        self.max_tracked_ips = max_tracked_ips
        self._requests: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = Lock()
        self._checks = 0

    def _client_ip(self, request: Request) -> str:
        peer_ip = request.client.host if request.client else "unknown"
        if peer_ip not in self.trusted_proxy_ips:
            return peer_ip
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for is None:
            return peer_ip
        # Walk toward the client only while the sender is trusted. A client can
        # prepend arbitrary addresses; those must never choose its limiter key.
        for hop in reversed(forwarded_for.split(",")):
            candidate = hop.strip()
            if not candidate:
                return peer_ip
            if candidate not in self.trusted_proxy_ips:
                return candidate
        return peer_ip

    def _sweep_expired(self, cutoff: float) -> None:
        for client_ip, timestamps in list(self._requests.items()):
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if not timestamps:
                del self._requests[client_ip]

    def check(self, request: Request) -> None:
        """Raise an API error when the request IP has exhausted its allowance."""
        client_ip = self._client_ip(request)
        now = monotonic()
        with self._lock:
            self._checks += 1
            if self._checks % _SWEEP_INTERVAL == 0:
                self._sweep_expired(now - self.window_seconds)
            if client_ip not in self._requests:
                if len(self._requests) >= self.max_tracked_ips:
                    self._requests.popitem(last=False)
                self._requests[client_ip] = deque()
            self._requests.move_to_end(client_ip)
            timestamps = self._requests[client_ip]
            while timestamps and timestamps[0] <= now - self.window_seconds:
                timestamps.popleft()
            if len(timestamps) >= self.limit:
                raise api_error(429, "RATE_LIMITED", "Too many authentication attempts")
            timestamps.append(now)
