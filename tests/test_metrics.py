"""CloudWatch metric tests - no real AWS calls are made."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import metrics


class FakeClient:
    def __init__(self):
        self.calls = []

    def put_metric_data(self, **kwargs):
        self.calls.append(kwargs)


def test_disabled_sends_nothing():
    os.environ["ENABLE_CLOUDWATCH"] = "false"
    fake = FakeClient()
    metrics._client = fake
    assert metrics.record_request({"cache_hit": False, "timings_ms": {"db": 1.2}}) is False
    assert fake.calls == []


def test_cache_miss_sends_latency_and_usage():
    os.environ["ENABLE_CLOUDWATCH"] = "true"
    fake = FakeClient()
    metrics._client = fake
    assert metrics.record_request({"cache_hit": False, "timings_ms": {"db": 1.5, "docs": 2.5}})
    names = [m["MetricName"] for m in fake.calls[0]["MetricData"]]
    assert fake.calls[0]["Namespace"] == "ContextRouter"
    assert names.count("SourceLatencyMs") == 2 and names.count("SourceUsed") == 2
    assert names.count("CacheHit") == 1


def test_cache_hit_sends_only_cache_metric():
    os.environ["ENABLE_CLOUDWATCH"] = "true"
    fake = FakeClient()
    metrics._client = fake
    metrics.record_request({"cache_hit": True, "timings_ms": {"db": 9.9}})
    data = fake.calls[0]["MetricData"]
    assert [m["MetricName"] for m in data] == ["CacheHit"] and data[0]["Value"] == 1


def test_aws_failure_does_not_crash():
    os.environ["ENABLE_CLOUDWATCH"] = "true"

    class Broken:
        def put_metric_data(self, **kw):
            raise RuntimeError("no network")

    metrics._client = Broken()
    assert metrics.record_request({"cache_hit": False, "timings_ms": {"db": 1}}) is False


if __name__ == "__main__":
    test_disabled_sends_nothing(); test_cache_miss_sends_latency_and_usage()
    test_cache_hit_sends_only_cache_metric(); test_aws_failure_does_not_crash()
    print("all metrics tests passed")