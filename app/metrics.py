"""Send per-source usage and latency to Amazon CloudWatch (optional).

Turn on with ENABLE_CLOUDWATCH=true in .env. If it is off, or AWS fails,
the app keeps working and nothing is sent.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

NAMESPACE = "ContextRouter"
_client = None


def _enabled() -> bool:
    return os.getenv("ENABLE_CLOUDWATCH", "false").lower() == "true"


def _get_client():
    global _client
    if _client is None:
        import boto3

        _client = boto3.client("cloudwatch", region_name=os.getenv("AWS_REGION", "us-east-1"))
    return _client


def build_metrics(result: dict) -> list:
    """Turn one /ask result into CloudWatch metric data."""
    cache_hit = bool(result.get("cache_hit"))

    data = [{"MetricName": "CacheHit", "Value": 1 if cache_hit else 0, "Unit": "Count"}]
    if not cache_hit:  # a cache hit calls no sources, so there is no new latency to report
        for source, ms in (result.get("timings_ms") or {}).items():
            dims = [{"Name": "Source", "Value": source}]
            data.append({"MetricName": "SourceLatencyMs", "Dimensions": dims,
                         "Value": float(ms), "Unit": "Milliseconds"})
            data.append({"MetricName": "SourceUsed", "Dimensions": dims,
                         "Value": 1, "Unit": "Count"})
    return data


def record_request(result: dict) -> bool:
    if not _enabled():
        return False
    try:
        _get_client().put_metric_data(Namespace=NAMESPACE, MetricData=build_metrics(result))
        return True
    except Exception as e:  # never let monitoring break the app
        print(f"[cloudwatch] failed ({type(e).__name__}: {e})")
        return False