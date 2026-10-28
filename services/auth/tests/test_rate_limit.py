"""Unit tests for bounded and proxy-aware IP rate limiting."""

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.rate_limit import IpRateLimiter


def _request(peer_ip: str, forwarded_for: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode()))
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/auth/login",
            "headers": headers,
            "client": (peer_ip, 1234),
        }
    )


def test_forwarded_ip_requires_trusted_proxy() -> None:
    """Only an allowlisted peer can supply the rate-limit client address."""
    trusted_limiter = IpRateLimiter(limit=1, trusted_proxy_ips={"10.0.0.1"})
    trusted_limiter.check(_request("10.0.0.1", "192.0.2.1"))
    trusted_limiter.check(_request("10.0.0.1", "192.0.2.2"))

    untrusted_limiter = IpRateLimiter(limit=1, trusted_proxy_ips={"10.0.0.1"})
    untrusted_limiter.check(_request("10.0.0.2", "192.0.2.1"))
    with pytest.raises(HTTPException) as error:
        untrusted_limiter.check(_request("10.0.0.2", "192.0.2.2"))
    assert error.value.status_code == 429


def test_tracked_ip_count_is_bounded() -> None:
    """Rotating source addresses cannot grow limiter state without bound."""
    limiter = IpRateLimiter(limit=1, max_tracked_ips=2)

    limiter.check(_request("192.0.2.1"))
    limiter.check(_request("192.0.2.2"))
    limiter.check(_request("192.0.2.3"))

    limiter.check(_request("192.0.2.1"))


def test_forwarded_chain_uses_rightmost_untrusted_hop() -> None:
    """An attacker cannot rotate a spoofed prefix behind a trusted proxy chain."""
    limiter = IpRateLimiter(limit=1, trusted_proxy_ips={"10.0.0.1", "10.0.0.2"})
    limiter.check(_request("10.0.0.1", "192.0.2.1, 198.51.100.8, 10.0.0.2"))
    with pytest.raises(HTTPException) as error:
        limiter.check(_request("10.0.0.1", "192.0.2.99, 198.51.100.8, 10.0.0.2"))
    assert error.value.status_code == 429


@pytest.mark.parametrize(
    "trusted_peer",
    ["2001:db8::1", "2001:0db8:0000:0000:0000:0000:0000:0001"],
)
def test_ipv6_proxy_and_client_spellings_share_allowance(trusted_peer: str) -> None:
    """Equivalent peer, proxy and client literals cannot split limiter buckets."""
    limiter = IpRateLimiter(
        limit=1,
        trusted_proxy_ips={trusted_peer, "2001:db8::2"},
    )
    limiter.check(
        _request(
            "2001:0db8::1",
            "192.0.2.1, 2001:0db8:0000:0000:0000:0000:0000:0003, 2001:0db8::2",
        )
    )
    with pytest.raises(HTTPException) as error:
        limiter.check(_request("2001:db8::1", "192.0.2.99, 2001:db8::3, 2001:db8::2"))
    assert error.value.status_code == 429


def test_malformed_forwarded_hop_stops_trusted_proxy_traversal() -> None:
    """Unparsable hops are untrusted, even when followed by trusted proxies."""
    limiter = IpRateLimiter(limit=1, trusted_proxy_ips={"2001:db8::1", "2001:db8::2"})
    limiter.check(_request("2001:db8::1", "192.0.2.1, not-an-ip, 2001:db8::2"))
    with pytest.raises(HTTPException) as error:
        limiter.check(_request("2001:db8::1", "192.0.2.99, not-an-ip, 2001:db8::2"))
    assert error.value.status_code == 429
