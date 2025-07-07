-- Sliding Window algorithm implementation for rate limiting.
-- ARGV[1]: period - The window period in seconds.
-- ARGV[2]: limit - Maximum allowed requests per window.
-- ARGV[3]: cost - Weight of the current request.
-- ARGV[4]: now_ms - Current time in milliseconds.
-- KEYS[1]: key - Redis key storing the current window count.
-- KEYS[2]: previous - Redis key storing the previous window count.

local period = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local cost = tonumber(ARGV[3])
local now_ms = tonumber(ARGV[4])

local exists = true
local current = redis.call("GET", KEYS[1])
if current == false then
    -- Initialize the current window count if it doesn't exist.
    current = 0
    exists = false
end

-- Get previous window count.
local previous = redis.call("GET", KEYS[2])
if previous == false then
    -- Default to 0 if previous window count doesn't exist.
    previous = 0
end

-- Calculate the current window count proportion.
-- For example, if the period is 10 seconds, and the current time is 1234567890,
-- the current window count proportion is (1234567890 % 10000) / 10000 = 0.23456789.
local period_ms = period * 1000
local current_proportion = (now_ms % period_ms) / period_ms
local previous_proportion = 1- current_proportion
-- Calculate the previous window count proportion.
previous = math.floor(previous_proportion * previous)

local retry_after = 0
local used = previous + current + cost
local limited = used > limit and cost ~= 0
if limited then
    if cost <= previous then
        retry_after = previous_proportion * period * cost / previous
    else
        -- |-- previous --|- current -|------- new period -------|
        retry_after = previous_proportion * period
    end
else
    -- Update the current window count.
    current = current + cost
    if not exists then
        -- Set expiration only for the first request in a new window.
        redis.call("EXPIRE", KEYS[1], 3 * period)
    end
    -- Store the updated current count.
    redis.call("SET", KEYS[1], current)
end

-- Return [limited, current]
-- limited: 1 if over limit, 0 otherwise.
-- current: current count in current window.
-- retry_after: time in seconds to wait before retrying.
return {limited, used, tostring(retry_after)}
