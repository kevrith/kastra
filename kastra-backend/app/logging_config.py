"""
Centralised logging: JSON lines in production (machine-parseable by Render /
any log aggregator), human-readable in development. Every log record carries
the request ID set by RequestIDMiddleware so a single request can be traced
end-to-end across app logs, access logs, and Sentry.
"""

import json
import logging
import logging.config
import time
import uuid
from contextvars import ContextVar

from starlette.types import ASGIApp, Receive, Scope, Send

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

access_logger = logging.getLogger("kastra.access")


class RequestIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        for extra_key in ("method", "path", "status_code", "duration_ms", "client_ip"):
            if hasattr(record, extra_key):
                payload[extra_key] = getattr(record, extra_key)
        return json.dumps(payload, default=str)


def setup_logging(production: bool) -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {"request_id": {"()": RequestIDFilter}},
            "formatters": {
                "json": {"()": JSONFormatter},
                "console": {
                    "format": "%(asctime)s %(levelname)-8s [%(request_id)s] %(name)s: %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "formatter": "json" if production else "console",
                    "filters": ["request_id"],
                },
            },
            "root": {"handlers": ["default"], "level": "INFO"},
            "loggers": {
                # uvicorn's own access log is replaced by our request log
                # (which includes request IDs and durations)
                "uvicorn.access": {"handlers": [], "propagate": False},
                "uvicorn.error": {"level": "INFO"},
            },
        }
    )


class RequestIDMiddleware:
    """
    Pure ASGI middleware: assigns each request an ID (honours an incoming
    X-Request-ID from a trusted proxy, else generates one), exposes it to all
    log records via a contextvar, echoes it back in the X-Request-ID response
    header, and emits one structured access-log line per request.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = dict(scope.get("headers") or []).get(b"x-request-id")
        request_id = incoming.decode()[:64] if incoming else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        start = time.perf_counter()
        status_holder = {"status": 500}

        async def send_with_request_id(message: dict) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            path = scope.get("path", "")
            if path != "/health":  # keep health-check noise out of the logs
                client = scope.get("client")
                access_logger.info(
                    "%s %s -> %d",
                    scope.get("method", "-"),
                    path,
                    status_holder["status"],
                    extra={
                        "method": scope.get("method", "-"),
                        "path": path,
                        "status_code": status_holder["status"],
                        "duration_ms": round((time.perf_counter() - start) * 1000, 1),
                        "client_ip": client[0] if client else "-",
                    },
                )
            request_id_var.reset(token)
