from opentelemetry.metrics import get_meter
from throttled import Throttled
from throttled.contrib.otel import OTelHook

# Create OTelHook with a meter from the OTel API.
# The actual metrics backend (e.g., Prometheus, OTLP) is configured separately
# via opentelemetry-sdk or your framework's setup.
meter = get_meter("throttled-example")

# Create a rate limiter with OTelHook attached.
throttle = Throttled(key="/api/ping", quota="5/m", hooks=[OTelHook(meter)])


def main() -> None:
    # First 5 requests are allowed.
    for i in range(5):
        result = throttle.limit("/api/ping")
        print(f"Request {i + 1}: {'denied' if result.limited else 'allowed'}")

    # But 6th request is denied.
    result = throttle.limit("/api/ping")
    print(f"Request 6: {'denied' if result.limited else 'allowed'}")

    # 📊 OTelHook records the following metrics:
    #   - throttled.requests (Counter): number of rate limit checks
    #   - throttled.duration (Histogram): latency of rate limit checks
    # Attributes: key, algorithm, store_type, result ("allowed" / "denied")


if __name__ == "__main__":
    main()
