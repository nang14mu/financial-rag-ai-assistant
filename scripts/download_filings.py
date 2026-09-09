"""Script to dynamically discover and download the 3 most recent 10-K filings for AAPL, MSFT, NVDA."""
import os
import sys
import yaml
import logging

sys.path.insert(0, os.path.abspath("src"))

from financial_ai.ingestion.sec_client import SECClient
from financial_ai.ingestion.filing_downloader import FilingDownloader

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    config_path = "./configs/companies.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        companies_cfg = yaml.safe_load(f).get("companies", {})

    client = SECClient()
    downloader = FilingDownloader(client=client)

    for ticker, info in companies_cfg.items():
        cik = info["cik"]
        logger.info("Discovering top 3 recent 10-K filings for %s (CIK: %s)...", ticker, cik)
        filings = downloader.download_top_3_filings(ticker=ticker, cik=cik)
        for f in filings:
            logger.info("-> %s FY%d 10-K saved at %s", ticker, f.fiscal_year, f.local_path)


if __name__ == "__main__":
    main()
