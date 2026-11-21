import logging
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("vaultguard.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
        request.state.trace_id = trace_id
        start_time = time.perf_counter()

        logger.info(
            f"[{trace_id}] Started {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}"
        )

        try:
            response = await call_next(request)
            process_time = (time.perf_counter() - start_time) * 1000
            response.headers["X-Trace-Id"] = trace_id
            response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"

            logger.info(
                f"[{trace_id}] Completed {request.method} {request.url.path} with status {response.status_code} in {process_time:.2f}ms"
            )
            return response
        except Exception as e:
            process_time = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[{trace_id}] Unhandled error on {request.method} {request.url.path} after {process_time:.2f}ms: {str(e)}",
                exc_info=True,
            )
            raise

