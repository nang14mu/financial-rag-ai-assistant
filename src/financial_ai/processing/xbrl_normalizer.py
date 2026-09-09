"""Normalizer for SEC Company Facts XBRL JSON extracting facts with full provenance."""
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from financial_ai.processing.metric_mapper import MetricMapper

logger = logging.getLogger(__name__)


class XBRLNormalizer:
    """Extracts and normalizes financial facts from raw SEC XBRL Company Facts JSON."""

    def __init__(self, metric_mapper: Optional[MetricMapper] = None, output_dir: str = "./data/processed/financial_facts"):
        self.metric_mapper = metric_mapper or MetricMapper()
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def normalize_company_facts(
        self,
        raw_facts_json: Dict[str, Any],
        ticker: str,
        target_fiscal_years: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        """Extract standardized facts with complete provenance for target fiscal years."""
        ticker = ticker.upper()
        us_gaap_data = raw_facts_json.get("facts", {}).get("us-gaap", {})
        if not us_gaap_data:
            logger.warning("No us-gaap facts found for %s", ticker)
            return []

        all_metrics = self.metric_mapper.get_all_metrics()
        extracted_facts: Dict[tuple, Dict[str, Any]] = {}

        for metric_code in all_metrics.keys():
            tags = self.metric_mapper.get_tags_for_metric(metric_code)
            
            for tag in tags:
                concept_data = us_gaap_data.get(tag)
                if not concept_data:
                    continue

                units_dict = concept_data.get("units", {})
                for unit_name, entries in units_dict.items():
                    for item in entries:
                        form = item.get("form", "")
                        fp = item.get("fp", "")
                        fy = item.get("fy")
                        val = item.get("val")
                        end_date_str = item.get("end")

                        # Target full annual 10-K reports
                        if form not in ("10-K", "10-K/A") or fp != "FY" or fy is None or val is None or not end_date_str:
                            continue

                        if target_fiscal_years and fy not in target_fiscal_years:
                            continue

                        key = (ticker, metric_code, fy, fp)
                        
                        # Only keep latest filed or 10-K if duplicate
                        if key in extracted_facts:
                            continue

                        filed_date_str = item.get("filed")
                        start_date_str = item.get("start")

                        fact_record = {
                            "ticker": ticker,
                            "metric_code": metric_code,
                            "fiscal_year": int(fy),
                            "fiscal_period": fp,
                            "start_date": datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else None,
                            "end_date": datetime.strptime(end_date_str, "%Y-%m-%d").date(),
                            "value": float(val),
                            "unit": unit_name,
                            "concept": tag,
                            "accession_number": item.get("accn"),
                            "form": form,
                            "filed_date": datetime.strptime(filed_date_str, "%Y-%m-%d").date() if filed_date_str else None,
                            "source": "SEC_COMPANY_FACTS",
                        }
                        extracted_facts[key] = fact_record

        normalized_list = list(extracted_facts.values())
        logger.info(
            "Normalized %d financial facts for %s across years %s",
            len(normalized_list),
            ticker,
            sorted(list(set(f["fiscal_year"] for f in normalized_list))),
        )
        return normalized_list

    def save_normalized_facts(self, facts: List[Dict[str, Any]], ticker: str) -> str:
        """Save normalized facts to JSON file."""
        out_path = os.path.join(self.output_dir, f"{ticker.upper()}_facts.json")
        # Convert date objects to string for JSON serialization
        serializable = []
        for f in facts:
            item = dict(f)
            if item.get("start_date"):
                item["start_date"] = str(item["start_date"])
            if item.get("end_date"):
                item["end_date"] = str(item["end_date"])
            if item.get("filed_date"):
                item["filed_date"] = str(item["filed_date"])
            serializable.append(item)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2)
        logger.info("Saved %d facts to %s", len(serializable), out_path)
        return out_path
