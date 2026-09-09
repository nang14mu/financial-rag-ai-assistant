"""Metric mapper connecting diverse US-GAAP taxonomy concepts to standardized financial metrics."""
import os
import yaml
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class MetricMapper:
    """Handles multi-tag US-GAAP concept mapping and prioritization."""

    def __init__(self, config_path: str = "./configs/metrics.yaml"):
        self.config_path = config_path
        self.metrics_config: Dict[str, Any] = {}
        self.tag_to_metric: Dict[str, str] = {}
        self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_path):
            logger.warning("Metrics config not found at %s. Using default mappings.", self.config_path)
            return

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            self.metrics_config = data.get("metrics", {})

        # Build reverse index for fast lookup: US-GAAP tag -> standard metric_code
        for metric_code, info in self.metrics_config.items():
            for tag in info.get("us_gaap_tags", []):
                # Don't overwrite if already mapped to a higher priority metric
                if tag not in self.tag_to_metric:
                    self.tag_to_metric[tag] = metric_code

    def get_standard_metric(self, us_gaap_tag: str) -> Optional[str]:
        """Resolve a US-GAAP tag to standard metric code."""
        return self.tag_to_metric.get(us_gaap_tag)

    def get_tags_for_metric(self, metric_code: str) -> List[str]:
        """Get the prioritized list of US-GAAP tags for a metric."""
        return self.metrics_config.get(metric_code, {}).get("us_gaap_tags", [])

    def get_metric_info(self, metric_code: str) -> Dict[str, Any]:
        """Get metadata details of a standard metric."""
        return self.metrics_config.get(metric_code, {})

    def get_all_metrics(self) -> Dict[str, Any]:
        """Return all standard metrics definitions."""
        return self.metrics_config
