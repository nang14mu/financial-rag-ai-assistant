"""Downloader for dynamic 10-K filings using SEC Submissions API."""
import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from financial_ai.ingestion.sec_client import SECClient
from financial_ai.ingestion.schemas import FilingMetadata

logger = logging.getLogger(__name__)


class FilingDownloader:
    """Discovers and downloads the 3 most recent 10-K filings dynamically per company."""

    def __init__(self, client: Optional[SECClient] = None, output_base_dir: str = "./data/raw/filings"):
        self.client = client or SECClient()
        self.output_base_dir = output_base_dir
        os.makedirs(self.output_base_dir, exist_ok=True)

    def get_recent_10k_metadata(self, ticker: str, cik: str, limit: int = 3) -> List[FilingMetadata]:
        """Query SEC Submissions API to discover the latest valid 10-K filings dynamically."""
        ticker = ticker.upper()
        clean_cik = cik.strip().zfill(10)
        cik_num = str(int(clean_cik))  # for SEC archives URL path

        url = f"https://data.sec.gov/submissions/CIK{clean_cik}.json"
        logger.info("Fetching submissions metadata for %s (CIK: %s)", ticker, clean_cik)
        response = self.client.get(url)
        data = response.json()

        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accession_nums = recent.get("accessionNumber", [])
        filing_dates = recent.get("filingDate", [])
        report_dates = recent.get("reportDate", [])
        primary_docs = recent.get("primaryDocument", [])

        filings: List[FilingMetadata] = []
        seen_years = set()

        for i, form_type in enumerate(forms):
            if form_type == "10-K":
                acc_num = accession_nums[i]
                acc_clean = acc_num.replace("-", "")
                p_doc = primary_docs[i]
                f_date_str = filing_dates[i]
                r_date_str = report_dates[i]

                f_date = datetime.strptime(f_date_str, "%Y-%m-%d").date()
                r_date = datetime.strptime(r_date_str, "%Y-%m-%d").date()
                
                # Determine fiscal year from report date or filing date
                # For NVDA: report date in Jan 2024 corresponds to FY2024
                # For MSFT: report date in June 2024 corresponds to FY2024
                # For AAPL: report date in Sept 2024 corresponds to FY2024
                fiscal_year = r_date.year

                # Avoid duplicate filings for the same fiscal year (e.g. amendments)
                if fiscal_year in seen_years:
                    continue
                seen_years.add(fiscal_year)

                doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{acc_clean}/{p_doc}"

                meta = FilingMetadata(
                    ticker=ticker,
                    cik=clean_cik,
                    accession_number=acc_num,
                    form="10-K",
                    filing_date=f_date,
                    report_date=r_date,
                    fiscal_year=fiscal_year,
                    primary_document=p_doc,
                    document_url=doc_url,
                )
                filings.append(meta)
                if len(filings) >= limit:
                    break

        logger.info("Discovered %d recent 10-K filings for %s: %s", len(filings), ticker, [f.fiscal_year for f in filings])
        return filings

    def download_filing(self, metadata: FilingMetadata, force_refresh: bool = False) -> str:
        """Download single 10-K filing HTML document to data/raw/filings/{ticker}/."""
        ticker_dir = os.path.join(self.output_base_dir, metadata.ticker)
        os.makedirs(ticker_dir, exist_ok=True)

        target_file = os.path.join(
            ticker_dir, f"{metadata.ticker}_{metadata.fiscal_year}_10K.html"
        )
        meta_file = os.path.join(
            ticker_dir, f"{metadata.ticker}_{metadata.fiscal_year}_meta.json"
        )

        if os.path.exists(target_file) and not force_refresh:
            logger.info("Filing already cached at %s", target_file)
            metadata.local_path = target_file
            return target_file

        logger.info("Downloading 10-K for %s FY%d from %s", metadata.ticker, metadata.fiscal_year, metadata.document_url)
        resp = self.client.get(metadata.document_url)

        with open(target_file, "w", encoding="utf-8", errors="ignore") as f:
            f.write(resp.text)

        metadata.local_path = target_file
        with open(meta_file, "w", encoding="utf-8") as f:
            f.write(metadata.model_dump_json(indent=2))

        logger.info(
            "Saved %s FY%d 10-K (%d bytes) to %s",
            metadata.ticker,
            metadata.fiscal_year,
            os.path.getsize(target_file),
            target_file,
        )
        return target_file

    def download_top_3_filings(self, ticker: str, cik: str, force_refresh: bool = False) -> List[FilingMetadata]:
        """Discover and download the 3 most recent 10-Ks for a company."""
        filings = self.get_recent_10k_metadata(ticker, cik, limit=3)
        for f in filings:
            self.download_filing(f, force_refresh=force_refresh)
        return filings
