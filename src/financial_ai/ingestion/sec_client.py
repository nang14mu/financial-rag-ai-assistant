"""SEC EDGAR API Client with rate limiting, custom User-Agent, and exponential backoff."""
import os
import time
import logging
from typing import Optional, Dict, Any
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class SECClient:
    """Client for querying SEC EDGAR APIs and fetching submissions/filings."""

    def __init__(
        self,
        user_agent: Optional[str] = None,
        rate_limit_per_sec: float = 8.0,
        max_retries: int = 5,
        backoff_factor: float = 1.5,
    ):
        self.user_agent = user_agent or os.getenv(
            "SEC_USER_AGENT", "FinancialAIAssistant dev@example.com"
        )
        self.rate_limit_delay = 1.0 / rate_limit_per_sec
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.last_request_time = 0.0
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": "data.sec.gov"
        })

    def _wait_rate_limit(self):
        """Ensure rate limit is not exceeded."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        stream: bool = False,
    ) -> requests.Response:
        """Perform a GET request with rate limiting and exponential backoff retry."""
        retry_delay = 1.0
        merged_headers = dict(self.session.headers)
        if headers:
            merged_headers.update(headers)

        # Fix host header dynamically if not data.sec.gov
        if "www.sec.gov" in url:
            merged_headers["Host"] = "www.sec.gov"
        elif "data.sec.gov" in url:
            merged_headers["Host"] = "data.sec.gov"
        else:
            merged_headers.pop("Host", None)

        for attempt in range(1, self.max_retries + 1):
            self._wait_rate_limit()
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=merged_headers,
                    timeout=30,
                    stream=stream,
                )
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:
                    wait_time = int(response.headers.get("Retry-After", retry_delay * 2))
                    logger.warning(
                        "Rate limited (429) by SEC. Backing off for %ds (attempt %d/%d)",
                        wait_time,
                        attempt,
                        self.max_retries,
                    )
                    time.sleep(wait_time)
                elif response.status_code in (500, 502, 503, 504):
                    logger.warning(
                        "SEC server error %d. Retrying in %.1fs (attempt %d/%d)",
                        response.status_code,
                        retry_delay,
                        attempt,
                        self.max_retries,
                    )
                    time.sleep(retry_delay)
                else:
                    response.raise_for_status()
            except (requests.RequestException, requests.ConnectionError) as exc:
                if attempt == self.max_retries:
                    logger.error("Failed after %d attempts: %s", self.max_retries, exc)
                    raise
                time.sleep(retry_delay)

            retry_delay *= self.backoff_factor

        raise requests.HTTPError(f"Failed to fetch {url} after {self.max_retries} attempts.")
