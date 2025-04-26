from typing import Dict, Union

_StringLikeT = str
_NumberLikeT = Union[int, float]

KeyT = _StringLikeT
StoreValueT = _NumberLikeT
StoreDictValueT = Dict[KeyT, _NumberLikeT]
StoreBucketValueT = Union[_NumberLikeT, StoreDictValueT]

AtomicActionTypeT = str

RateLimiterTypeT = str

TimeLikeValueT = Union[int, float]
