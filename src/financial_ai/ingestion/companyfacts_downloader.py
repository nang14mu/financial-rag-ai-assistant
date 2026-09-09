"""Downloader for SEC Company Facts XBRL API."""
import os
import json
import logging
from typing import Optional, Dict, Any
from financial_ai.ingestion.sec_client import SECClient

logger = logging.getLogger(__name__)


class CompanyFactsDownloader:
    """Fetches and caches SEC Company Facts XBRL JSON for specified companies."""

    def __init__(self, client: Optional[SECClient] = None, output_dir: str = "./data/raw/xbrl"):
        self.client = client or SECClient()
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def download_company_facts(self, ticker: str, cik: str, force_refresh: bool = False) -> str:
        """Download CIK Company Facts JSON and save to output directory."""
        ticker = ticker.upper()
        clean_cik = cik.strip().zfill(10)
        file_path = os.path.join(self.output_dir, f"{ticker}_companyfacts.json")

        if os.path.exists(file_path) and not force_refresh:
            logger.info("Found cached Company Facts for %s at %s", ticker, file_path)
            return file_path

        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{clean_cik}.json"
        logger.info("Downloading Company Facts for %s (CIK: %s) from %s", ticker, clean_cik, url)

        response = self.client.get(url)
        data = response.json()

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info("Saved %s Company Facts (%d bytes) to %s", ticker, os.path.getsize(file_path), file_path)
        return file_path

    def load_company_facts(self, ticker: str, cik: Optional[str] = None) -> Dict[str, Any]:
        """Load Company Facts JSON from file, downloading if missing and CIK provided."""
        ticker = ticker.upper()
        file_path = os.path.join(self.output_dir, f"{ticker}_companyfacts.json")
        if not os.path.exists(file_path):
            if not cik:
                raise FileNotFoundError(f"Facts file not found for {ticker} and no CIK provided to download.")
            file_path = self.download_company_facts(ticker, cik)

        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
