"""Script to download SEC XBRL Company Facts JSON for AAPL, MSFT, and NVDA."""
import os
import sys
import yaml
import logging

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath("src"))

from financial_ai.ingestion.sec_client import SECClient
from financial_ai.ingestion.companyfacts_downloader import CompanyFactsDownloader

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    config_path = "./configs/companies.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        companies_cfg = yaml.safe_load(f).get("companies", {})

    client = SECClient()
    downloader = CompanyFactsDownloader(client=client)

    for ticker, info in companies_cfg.items():
        cik = info["cik"]
        logger.info("Processing Company Facts for %s (CIK: %s)...", ticker, cik)
        path = downloader.download_company_facts(ticker=ticker, cik=cik)
        logger.info("Saved %s facts to %s", ticker, path)


if __name__ == "__main__":
    main()
