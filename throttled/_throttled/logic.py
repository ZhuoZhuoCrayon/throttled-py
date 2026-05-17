from .. import constants, exceptions, rate_limiter, types, utils
from ..rate_limiter.quota_parser import parse as parse_quota


class ThrottledLogic:
    """Pure throttler logic shared by sync and async implementations."""

    # Non-blocking mode constant
    _NON_BLOCKING: float = -1
    # Interval between retries in seconds
    _WAIT_INTERVAL: float = 0.5
    # Minimum interval between retries in seconds
    _WAIT_MIN_INTERVAL: float = 0.2
    _DEFAULT_RATE_LIMITER_TYPE: types.RateLimiterTypeT = (
        constants.RateLimiterType.TOKEN_BUCKET.value
    )

    key: str | None
    timeout: float

    @classmethod
    def _validate_cost(cls, cost: int) -> None:
        """Validate the cost of the current request.

        :param cost: The cost of the current request in terms of how much of
            the rate limit quota it consumes.
            It must be an integer greater than or equal to 0.
        :raise: :class:`throttled.exceptions.DataError` if the cost is
            not a non-negative integer.
        """
        if isinstance(cost, int) and cost >= 0:
            return

        raise exceptions.DataError(
            f"Invalid cost: {cost}, must be an integer greater than or equal to 0."
        )

    @classmethod
    def _validate_timeout(cls, timeout: float) -> None:
        """Validate the timeout value.

        :param timeout: Maximum wait time in seconds when rate limit is exceeded.
        :raise: DataError if the timeout is not a positive float or -1(non-blocking).
        """
        if timeout == cls._NON_BLOCKING:
            return

        if isinstance(timeout, int | float) and timeout > 0:
            return

        raise exceptions.DataError(
            f"Invalid timeout: {timeout}, must be a positive float or -1(non-blocking)."
        )

    @classmethod
    def _parse_quota(cls, quota: rate_limiter.Quota | str | None) -> rate_limiter.Quota:
        if quota is None:
            return rate_limiter.per_min(60)

        if isinstance(quota, rate_limiter.Quota):
            return quota

        parsed_quotas = parse_quota(quota)
        if len(parsed_quotas) > 1:
            raise exceptions.DataError(
                "Invalid quota: multiple quota rules are not supported in "
                "Throttled(quota=...) yet."
            )
        return parsed_quotas[0]

    def _get_key(self, key: types.KeyT | None = None) -> types.KeyT:
        # Use the provided key if available.
        if key:
            return key

        if self.key:
            return self.key

        raise exceptions.DataError(f"Invalid key: {key}, must be a non-empty key.")

    def _get_timeout(self, timeout: float | None = None) -> float:
        if timeout is not None:
            self._validate_timeout(timeout)
            return timeout

        return self.timeout

    def _get_wait_time(self, retry_after: float) -> float:
        """Calculate the wait time based on the retry_after value."""
        # WAIT_INTERVAL: Chunked waiting interval to avoid long blocking periods.
        # Also helps reduce actual wait time considering thread context switches.
        # WAIT_MIN_INTERVAL: Minimum wait interval to prevent busy-waiting.
        return max(min(retry_after, self._WAIT_INTERVAL), self._WAIT_MIN_INTERVAL)

    @classmethod
    def _is_exit_waiting(
        cls, start_time: float, retry_after: float, timeout: float
    ) -> bool:
        # Calculate the elapsed time since the start time.
        # Due to additional context switching overhead in multithread contexts,
        # we don't directly use sleep_time to calculate elapsed time.
        # Instead, we re-fetch the current time and subtract it from the start time.
        elapsed: float = utils.now_mono_f() - start_time
        return elapsed >= retry_after or elapsed >= timeout
