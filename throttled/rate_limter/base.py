import abc
import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, List, Optional, Set, Type

from ..exceptions import SetUpError
from ..store import BaseAtomicAction, BaseStore
from ..types import AtomicActionTypeT, RateLimiterTypeT

logger: logging.Logger = logging.getLogger(__name__)


@dataclass
class Rate:
    """Rate represents the rate limit configuration."""

    # The time period for which the rate limit applies.
    period: timedelta

    # The maximum number of requests allowed within the specified period.
    limit: int


@dataclass
class Quota:
    """Quota represents the quota limit configuration."""

    # The base rate limit configuration.
    rate: Rate

    # Optional burst capacity that allows exceeding the rate limit momentarily.
    # Default is 0, which means no burst capacity.
    burst: int = 0

    def get_period_sec(self) -> int:
        return int(self.rate.period.seconds)

    def get_limit(self) -> int:
        return self.rate.limit


def per_sec(limit: int, burst: Optional[int] = None) -> Quota:
    """Create a quota representing the maximum requests and burst per second."""
    if burst is None:
        burst = limit
    return Quota(Rate(period=timedelta(seconds=1), limit=limit), burst=burst)


def per_min(limit: int, burst: Optional[int] = None) -> Quota:
    """Create a quota representing the maximum requests and burst per minute."""
    if burst is None:
        burst = limit
    return Quota(Rate(period=timedelta(minutes=1), limit=limit), burst=burst)


def per_hour(limit: int, burst: Optional[int] = None) -> Quota:
    """Create a quota representing the maximum requests and burst per hour."""
    if burst is None:
        burst = limit
    return Quota(Rate(period=timedelta(hours=1), limit=limit), burst=burst)


def per_day(limit: int, burst: Optional[int] = None) -> Quota:
    """Create a quota representing the maximum requests and burst per day."""
    return Quota(Rate(period=timedelta(days=1), limit=limit), burst=burst)


@dataclass
class RateLimitState:
    """RateLimitState represents the current state of the rate limiter for the given
    key."""

    # Limit represents the maximum number of requests allowed to pass in the initial
    # state.
    limit: int

    # Remaining represents the maximum number of requests allowed to pass for the given
    # key in the current state.
    remaining: int

    # ResetAfter represents the time in seconds for the RateLimiter to return to its
    # initial state. In the initial state, Limit=Remaining.
    reset_after: float

    # TODO RetryAfter represents the time in seconds for the request to be retried.


@dataclass
class RateLimitResult:
    """RateLimitState represents the result after executing the RateLimiter for the
    given key."""

    # Limited represents whether this request is allowed to pass.
    limited: bool

    state: RateLimitState


class RateLimiterRegistry:
    _RATE_LIMITERS: Dict[RateLimiterTypeT, Type["BaseRateLimiter"]] = {}

    @classmethod
    def register(cls, new_cls):
        try:
            cls._RATE_LIMITERS[new_cls.Meta.type] = new_cls
        except AttributeError as e:
            raise SetUpError("failed to register RateLimiter: {}".format(e))

    @classmethod
    def get(cls, _type: RateLimiterTypeT) -> Type["BaseRateLimiter"]:
        try:
            return cls._RATE_LIMITERS[_type]
        except KeyError:
            raise SetUpError("{} not found".format(_type))


class RateLimiterMeta(abc.ABCMeta):
    def __new__(cls, name, bases, attrs):
        new_cls = super().__new__(cls, name, bases, attrs)
        if not [b for b in bases if isinstance(b, RateLimiterMeta)]:
            return new_cls

        RateLimiterRegistry.register(new_cls)
        return new_cls


class BaseRateLimiter(metaclass=RateLimiterMeta):
    """Base class for RateLimiter."""

    KEY_PREFIX: str = "throttled:v1:"

    class Meta:
        type: RateLimiterTypeT = ""

    def __init__(
        self,
        quota: Quota,
        store: BaseStore,
        additional_atomic_actions: Optional[List[Type[BaseAtomicAction]]] = None,
    ) -> None:
        self.quota: Quota = quota
        self._store: BaseStore = store
        self._atomic_actions: Dict[AtomicActionTypeT, BaseAtomicAction] = {}
        self._register_atomic_actions(additional_atomic_actions or [])

    @classmethod
    @abc.abstractmethod
    def _default_atomic_action_classes(cls) -> List[Type[BaseAtomicAction]]:
        """Define the default AtomicAction classes for RateLimiter."""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def _supported_atomic_action_types(cls) -> List[AtomicActionTypeT]:
        """Define the supported AtomicAction types for RateLimiter."""
        raise NotImplementedError

    @abc.abstractmethod
    def _limit(self, key: str, cost: int) -> RateLimitResult:
        raise NotImplementedError

    @abc.abstractmethod
    def _peek(self, key: str) -> RateLimitState:
        raise NotImplementedError

    def try_register_atomic_action(self, action_cls: Type[BaseAtomicAction]) -> None:
        """Try to register AtomicAction class.
        :param action_cls: AtomicAction class to be registered.
        :raise: SetUpError
        """
        action_cls.match_or_raise(self._store.TYPE)
        self._atomic_actions[action_cls.TYPE] = self._store.make_atomic(action_cls)

    def _validate_registered_atomic_actions(self) -> None:
        """Validate that all required AtomicAction types have been registered.
        :raise: SetUpError
        """
        supported_types: Set[AtomicActionTypeT] = set(
            self._supported_atomic_action_types()
        )
        registered_types: Set[AtomicActionTypeT] = set(self._atomic_actions.keys())

        missing_types: Set[str] = supported_types - registered_types
        if missing_types:
            raise SetUpError(
                "Missing AtomicActionTypes: expected {expected} but missing "
                "{missing}.".format(expected=supported_types, missing=missing_types)
            )

    def _register_atomic_actions(self, classes: List[Type[BaseAtomicAction]]) -> None:
        """Register AtomicAction classes for default and additional classes."""
        for action_cls in self._default_atomic_action_classes() + classes:
            try:
                self.try_register_atomic_action(action_cls)
            except SetUpError as e:
                logger.debug(
                    "Failed to register AtomicAction class for %s: %s", action_cls, e
                )
                pass

        self._validate_registered_atomic_actions()

    def _prepare_key(self, key: str) -> str:
        """Prepare the key by adding the prefix.
        :param key: The unique identifier for the rate limit subject.
        :return: The formatted key with prefix.

        # Benchmarks(TokenBucket)
        # Python 3.13.1 (main, Mar 29 2025, 16:29:36) [Clang 15.0.0 (clang-1500.3.9.4)]
        # Implementation: CPython
        # OS: Darwin 23.6.0, Arch: arm64
        #
        # >> Redis baseline
        # command    -> set key value
        # serial     -> 🕒Latency: 0.0589 ms/op, 🚀Throughput: 16828 req/s (--)
        # concurrent -> 🕒Latency: 1.9032 ms/op, 💤Throughput: 16729 req/s (⬇️-0.59%)
        #
        # >> Before preparing key
        # serial     -> 🕒Latency: 0.0722 ms/op, 🚀Throughput: 13740 req/s (--)
        # concurrent -> 🕒Latency: 2.3197 ms/op, 🚀Throughput: 13742 req/s (⬆️0.01%)
        #
        # >> After preparing key
        # serial     -> 🕒Latency: 0.0724 ms/op, 🚀Throughput: 13712 req/s (--)
        # concurrent -> 🕒Latency: 2.3126 ms/op, 🚀Throughput: 13782 req/s (⬆️0.51%)
        """
        return f"{self.KEY_PREFIX}{self.Meta.type}:{key}"

    def limit(self, key: str, cost: int = 1) -> RateLimitResult:
        """Apply rate limiting logic to a given key with a specified cost.
        :param key: The unique identifier for the rate limit subject.
                    eg: user ID or IP address.
        :param cost: The cost of the current request in terms of how much of the rate
                     limit quota it consumes.
        :return: A tuple containing two elements:
                 - RateLimitResult: Representing the result after executing the
                                    RateLimiter for the given key.
                 - RateLimitState: Representing the current state of the RateLimiter for
                                   the given key.
        """
        return self._limit(key, cost)

    def peek(self, key: str) -> RateLimitState:
        """Retrieve the current state of rate limiter for the given key
           without actually modifying the state.
        :param key: The unique identifier for the rate limit subject.
                    eg: user ID or IP address.
        :return: RateLimitState - Representing the current state of the rate limiter
                                  for the given key.
        """
        return self._peek(key)
