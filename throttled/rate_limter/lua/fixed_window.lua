-- Fixed Window algorithm implementation for rate limiting.
-- ARGV[1]: period - The window period in seconds.
-- ARGV[2]: limit - Maximum allowed requests per window.
-- ARGV[3]: cost - Weight of the current request.
-- KEYS[1]: key - Redis key storing the current window count.

local period = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local cost = tonumber(ARGV[3])
local current = redis.call("INCRBY", KEYS[1], cost)

-- Set expiration only for first request in new window.
if current == cost then
    redis.call("EXPIRE", KEYS[1], period)
end

-- Return [limited, current]
-- is_limited: 1 if over limit, 0 otherwise.
-- current: current count in current window.
return {current > limit and 1 or 0, current}
