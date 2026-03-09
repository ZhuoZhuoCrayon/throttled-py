from opentelemetry.metrics import get_meter
from throttled import Throttled, rate_limiter
from throttled.contrib.otel import OTelHook

# Create OTelHook with a meter from the OTel API.
# The actual metrics backend (e.g., Prometheus, OTLP) is configured separately
# via opentelemetry-sdk or your framework's setup.
meter = get_meter("throttled-example")
hook = OTelHook(meter)

# Create a rate limiter with OTelHook attached.
throttle = Throttled(
    key="/api/ping",
    quota=rate_limiter.per_min(5),
    hooks=[hook],
)


def main():
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
