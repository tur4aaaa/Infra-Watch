import logging
import os
import time

import httpx

from agent.agent import collect_system_metrics

logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

BACKEND_URL = os.getenv("INFRAWATCH_BACKEND_URL", "http://127.0.0.1:8000")
SEND_INTERVAL = float(os.getenv("INFRAWATCH_SEND_INTERVAL", "10"))  # seconds
MAX_BACKOFF = 60


def send_metrics(client: httpx.Client, metrics: dict) -> bool:
    """Send metrics to the backend. Returns True if successful, False otherwise."""
    try:
        response = client.post(f"{BACKEND_URL}/metrics", json=metrics)
        response.raise_for_status() # Httpx does not raise an exception for 4xx or 5xx
        return True
    except httpx.HTTPStatusError as error:
        logger.error(
            "Backend rejected metrics: %s %s",
            error.response.status_code,
            error.response.text,
        )
    except httpx.RequestError as error:
        logger.warning("Backend is unreachable: %s", error)
    return False

def main():
    logger.info("Sending metrics to %s every %0f seconds", BACKEND_URL, SEND_INTERVAL)
    wait = SEND_INTERVAL

    with httpx.Client(timeout=5) as client:
        while True:
            started = time.monotonic()

            metrics = collect_system_metrics()

            if send_metrics(client, metrics):
                logger.info(
                    "Sent: CPU %.1f%% | MEM %.1f%%",
                    metrics["cpu_usage"],
                    metrics["memory"]["used_percent"],
                )
                wait = SEND_INTERVAL  # default wait time after successful send
            else:
                wait = min(wait * 2, MAX_BACKOFF)  # wait time doubles after each failure, up to MAX_BACKOFF
                logger.info("Retrying in %.0f s", wait)

            
            elapsed = time.monotonic() - started
            time.sleep(max(0, wait - elapsed))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Agent stopped")