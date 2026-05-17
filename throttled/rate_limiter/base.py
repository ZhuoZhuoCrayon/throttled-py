import abc
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Generic, Protocol, TypeVar

from .. import exceptions, types

logger: logging.Logger = logging.getLogger(__name__)

_RateLimiterT = TypeVar("_RateLimiterT", bound="BaseRateLimiterMixin")

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import ClassVar

    from ..store import BaseAtomicAction, BaseStore


@dataclass
class Rate:
    """Rate represents the rate limit configuration."""

    #: The time period for which the rate limit applies.
    period: timedelta

    #: The maximum number of requests allowed within the specified period.
    limit: int


@dataclass
class Quota:
    """Quota represents the quota limit configuration."""

    #: The base rate limit configuration.
    rate: Rate

    #: Optional burst capacity that allows exceeding the rate limit momentarily.
    #: Default is 0, which means no burst capacity.
    burst: int = 0

    #: The period in seconds.
    period_sec: int = field(init=False)
    #: The emission interval in seconds.
    emission_interval: float = field(init=False)
    #: The fill rate per second.
    fill_rate: float = field(init=False)

    def __post_init__(self) -> None:
        self.period_sec = int(self.rate.period.total_seconds())
        self.emission_interval = self.period_sec / self.rate.limit
        self.fill_rate = self.rate.limit / self.period_sec

    def get_period_sec(self) -> int:
        """Get the period in seconds."""
        return self.period_sec

    def get_limit(self) -> int:
        return self.rate.limit


def per_duration(duration: timedelta, limit: int, burst: int | None = None) -> Quota:
    """Create a quota representing the maximum requests and burst per duration."""
    if burst is None:
        burst = limit
    return Quota(Rate(period=duration, limit=limit), burst=burst)


def per_sec(limit: int, burst: int | None = None) -> Quota:
    """Create a quota representing the maximum requests and burst per second."""
    return per_duration(timedelta(seconds=1), limit, burst)


def per_min(limit: int, burst: int | None = None) -> Quota:
    """Create a quota representing the maximum requests and burst per minute."""
    return per_duration(timedelta(minutes=1), limit, burst)


def per_hour(limit: int, burst: int | None = None) -> Quota:
    """Create a quota representing the maximum requests and burst per hour."""
    return per_duration(timedelta(hours=1), limit, burst)


def per_day(limit: int, burst: int | None = None) -> Quota:
    """Create a quota representing the maximum requests and burst per day."""
    return per_duration(timedelta(days=1), limit, burst)


def per_week(limit: int, burst: int | None = None) -> Quota:
    """Create a quota representing the maximum requests and burst per week."""
    return per_duration(timedelta(weeks=1), limit, burst)


@dataclass
class RateLimitState:
    """Current state of the rate limiter for a given key."""

    #: Represents the maximum number of requests allowed to pass in the initial
    #: state.
    limit: int

    #: Represents the maximum number of requests allowed to pass for the given
    #: key in the current state.
    remaining: int

    #: Represents the time in seconds for the RateLimiter to return to its
    #: initial state. In the initial state, :attr:`limit` = :attr:`remaining`.
    reset_after: float

    #: Represents the time in seconds for the request to be retried, 0 if
    #: the request is allowed.
    retry_after: float = 0


class RateLimitResult:
    """Result produced by the rate limiter for a given key.

    Exposes whether the request was limited, plus a lazily-materialized
    :class:`RateLimitState` snapshot via the :attr:`state` property.
    """

    __slots__ = ("limited", "_state_values", "_state")

    def __init__(
        self, limited: bool, state_values: tuple[int, int, float, float]
    ) -> None:
        #: Represents whether this request is allowed to pass.
        self.limited: bool = limited
        self._state_values: tuple[int, int, float, float] = state_values
        self._state: RateLimitState | None = None

    @property
    def state(self) -> RateLimitState:
        if self._state:
            return self._state
        self._state = RateLimitState(*self._state_values)
        return self._state


class _RateLimiterRegistryP(Protocol):
    """Erased registry view used by the metaclass registration hook."""

    def register(self, new_cls: type[Any]) -> None:
        """Register a dynamically created RateLimiter class."""
        ...


class BaseRateLimiterRegistry(Generic[_RateLimiterT]):
    """Typed base registry for RateLimiter classes."""

    _NAMESPACE: "ClassVar[str]" = ""

    @classmethod
    def _rate_limiters(cls) -> dict[types.RateLimiterTypeT, type[_RateLimiterT]]:
        """Return the concrete RateLimiter class table."""
        raise NotImplementedError

    @classmethod
    def get_register_key(cls, _type: types.RateLimiterTypeT) -> str:
        """Get the register key for the RateLimiter classes."""
        return f"{cls._NAMESPACE}:{_type}"

    @classmethod
    def register(cls, new_cls: type[_RateLimiterT]) -> None:
        """Register a RateLimiter class."""
        try:
            cls._rate_limiters()[cls.get_register_key(new_cls.Meta.type)] = new_cls
        except AttributeError as e:
            raise exceptions.SetUpError(f"failed to register RateLimiter: {e}") from e

    @classmethod
    def get(cls, _type: types.RateLimiterTypeT) -> type[_RateLimiterT]:
        """Get a registered RateLimiter class."""
        try:
            return cls._rate_limiters()[cls.get_register_key(_type)]
        except KeyError:
            raise exceptions.SetUpError(f"{_type} not found") from None


class RateLimiterRegistry(BaseRateLimiterRegistry["BaseRateLimiter"]):
    """Registry for sync RateLimiter classes."""

    _NAMESPACE: "ClassVar[str]" = "sync"
    _RATE_LIMITERS: "ClassVar[dict[types.RateLimiterTypeT, type[BaseRateLimiter]]]" = {}

    @classmethod
    def _rate_limiters(cls) -> "dict[types.RateLimiterTypeT, type[BaseRateLimiter]]":
        """Return the sync RateLimiter class table."""
        return cls._RATE_LIMITERS


class RateLimiterMeta(abc.ABCMeta):
    """Metaclass for RateLimiter classes."""

    _REGISTRY_CLASS: _RateLimiterRegistryP = RateLimiterRegistry

    def __new__(
        cls, name: str, bases: tuple[type[Any], ...], attrs: dict[str, Any]
    ) -> "RateLimiterMeta":
        new_cls = super().__new__(cls, name, bases, attrs)
        if not [b for b in bases if isinstance(b, cls)]:
            return new_cls

        cls._REGISTRY_CLASS.register(new_cls)
        return new_cls


class BaseRateLimiterMixin(abc.ABC):
    """Mixin class for RateLimiter."""

    KEY_PREFIX: str = "throttled:v1:"

    quota: Quota

    class Meta:
        type: types.RateLimiterTypeT = ""

    @classmethod
    @abc.abstractmethod
    def _supported_atomic_action_types(cls) -> "Sequence[types.AtomicActionTypeT]":
        """Define the supported AtomicAction types for RateLimiter."""
        raise NotImplementedError

    @classmethod
    def _check_supported_atomic_action_types(
        cls, registered_types: "Sequence[types.AtomicActionTypeT]"
    ) -> None:
        """Check if the provided AtomicAction types are supported.

        :param registered_types: A sequence of AtomicAction types to check.
        :raise: SetUpError if any of the provided types are not supported.
        """
        supported_types: set[types.AtomicActionTypeT] = set(
            cls._supported_atomic_action_types()
        )
        missing_types: set[str] = supported_types - set(registered_types)
        if missing_types:
            raise exceptions.SetUpError(
                "Missing AtomicActionTypes: expected [{expected}] but missing "
                "[{missing}].".format(
                    expected=",".join(sorted(supported_types)),
                    missing=",".join(sorted(missing_types)),
                )
            )

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


class BaseRateLimiter(BaseRateLimiterMixin, abc.ABC, metaclass=RateLimiterMeta):
    """Base class for RateLimiter."""

    _store: "BaseStore"
    _atomic_actions: "dict[types.AtomicActionTypeT, BaseAtomicAction]"

    _DEFAULT_ATOMIC_ACTION_CLASSES: "Sequence[type[BaseAtomicAction]]" = ()

    def __init__(
        self,
        quota: Quota,
        store: "BaseStore",
        additional_atomic_actions: "Sequence[type[BaseAtomicAction]] | None" = None,
    ) -> None:
        self.quota: Quota = quota
        self._store = store
        self._atomic_actions = {}
        self._register_atomic_actions(additional_atomic_actions or [])

    @classmethod
    def _default_atomic_action_classes(cls) -> "Sequence[type[BaseAtomicAction]]":
        """Return the default AtomicAction classes for RateLimiter."""
        return cls._DEFAULT_ATOMIC_ACTION_CLASSES

    def _validate_registered_atomic_actions(self) -> None:
        self._check_supported_atomic_action_types(list(self._atomic_actions.keys()))

    def _register_atomic_actions(
        self, classes: "Sequence[type[BaseAtomicAction]]"
    ) -> None:
        """Register AtomicAction classes for default and additional classes."""
        all_classes: list[type[BaseAtomicAction]] = list(
            self._default_atomic_action_classes()
        ) + list(classes)
        for action_cls in all_classes:
            if action_cls.STORE_TYPE != self._store.TYPE:
                continue
            self._atomic_actions[action_cls.TYPE] = self._store.make_atomic(action_cls)

        self._validate_registered_atomic_actions()

    @abc.abstractmethod
    def _limit(self, key: str, cost: int) -> RateLimitResult:
        raise NotImplementedError

    @abc.abstractmethod
    def _peek(self, key: str) -> RateLimitState:
        raise NotImplementedError

    def limit(self, key: str, cost: int = 1) -> RateLimitResult:
        """Apply rate limiting logic to a given key with a specified cost.

        :param key: The unique identifier for the rate limit subject.
                    eg: user ID or IP address.
        :param cost: The cost of the current request in terms of how much of the rate
                     limit quota it consumes.
                     It must be an integer greater than or equal to 0.
        :return: A tuple containing two elements:
                 - RateLimitResult: Representing the result after executing the
                                    RateLimiter for the given key.
                 - RateLimitState: Representing the current state of the RateLimiter for
                                   the given key.
        """
        return self._limit(key, cost)

    def peek(self, key: str) -> RateLimitState:
        """Retrieve the current state of rate limiter for the given key.

        :param key: The unique identifier for the rate limit subject.
                    eg: user ID or IP address.
        :return: RateLimitState - Representing the current state of the rate limiter
                                  for the given key.
        """
        return self._peek(key)
