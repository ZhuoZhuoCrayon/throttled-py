class BaseThrottledError(Exception):
    pass


class SetUpError(BaseThrottledError):
    pass


class DataError(BaseThrottledError):
    pass


class StoreUnavailableError(BaseThrottledError):
    pass


class LimitedError(BaseThrottledError):
    pass
