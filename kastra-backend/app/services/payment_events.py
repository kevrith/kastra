"""
In-process SSE event bus for real-time payment notifications.
Maps invoice_id → list of asyncio.Queue so the M-Pesa / Paystack callback
can push a single payment event to every browser tab waiting on that invoice.

Single-server only. For multi-server deployments, replace with Redis pub/sub.
"""
import asyncio
import json
from collections import defaultdict
from typing import AsyncGenerator

_subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)

_HEARTBEAT_INTERVAL = 25  # seconds — keeps proxies from closing idle connections


def subscribe(invoice_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=10)
    _subscribers[invoice_id].append(q)
    return q


def unsubscribe(invoice_id: str, q: asyncio.Queue) -> None:
    subs = _subscribers.get(invoice_id)
    if subs and q in subs:
        subs.remove(q)
    if not subs:
        _subscribers.pop(invoice_id, None)


async def publish(invoice_id: str, data: dict) -> None:
    for q in list(_subscribers.get(invoice_id, [])):
        try:
            q.put_nowait(data)
        except asyncio.QueueFull:
            pass  # slow consumer — drop rather than block the callback


async def stream_events(invoice_id: str) -> AsyncGenerator[str, None]:
    q = subscribe(invoice_id)
    try:
        yield "retry: 3000\n"
        yield "event: connected\ndata: {}\n\n"
        while True:
            try:
                data = await asyncio.wait_for(q.get(), timeout=_HEARTBEAT_INTERVAL)
                yield f"event: payment\ndata: {json.dumps(data)}\n\n"
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"
    finally:
        unsubscribe(invoice_id, q)
