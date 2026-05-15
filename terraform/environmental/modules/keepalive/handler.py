import os
import time
from urllib.parse import urlparse

import pg8000.native


def handler(event, context):
    url = urlparse(os.environ["DATABASE_URL"])
    start = time.monotonic()
    conn = pg8000.native.Connection(
        host=url.hostname,
        port=url.port or 5432,
        user=url.username,
        password=url.password,
        database=url.path.lstrip("/"),
        timeout=45,
    )
    conn.run("SELECT 1")
    conn.close()
    latency_ms = round((time.monotonic() - start) * 1000)
    return {"status": "ok", "latency_ms": latency_ms}
