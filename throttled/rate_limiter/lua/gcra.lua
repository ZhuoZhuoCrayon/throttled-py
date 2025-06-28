-- GCRA (Generic Cell Rate Algorithm) implementation for rate limiting.
-- Inspire by [Rate Limiting, Cells, and GCRA](https://brandur.org/rate-limiting).
-- ARGV[1]: emission_interval - Time interval to add one Token.
-- ARGV[2]: capacity - Maximum number of tokens.
-- ARGV[3]: cost - Number of tokens required for the current request.
-- KEYS[1]: Redis key to store the last token generation time.

local emission_interval = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local cost = tonumber(ARGV[3])

local jan_1_2025 = 1735660800
local now = redis.call("TIME")
now = (now[1] - jan_1_2025) + (now[2] / 1000000)

local last_tat = redis.call("GET", KEYS[1])
if not last_tat then
    last_tat = now
else
    last_tat = tonumber(last_tat)
end

-- Calculate the fill time required for the current cost.
local fill_time_for_cost = cost * emission_interval
-- Calculate the fill time required for the full capacity.
local fill_time_for_capacity = capacity * emission_interval
-- Calculate the theoretical arrival time (TAT) for the current request.
local tat = math.max(now, last_tat) + fill_time_for_cost
-- Calculate the the time when the request would be allowed.
local allow_at = tat - fill_time_for_capacity
-- Calculate the time elapsed since the request would be allowed.
local time_elapsed = now - allow_at


local limited = 0
local retry_after = 0
local reset_after = tat - now
local remaining = math.floor(time_elapsed / emission_interval)
if remaining < 0 then
    limited = 1
    retry_after = time_elapsed * -1
    reset_after = math.max(0, last_tat - now)
    remaining = math.min(capacity, cost + remaining)
else
    if reset_after > 0 then
        redis.call("SET", KEYS[1], tat, "EX", math.ceil(reset_after))
    end
end

-- Return [limited, remaining, reset_after, retry_after]
-- limited: 1 if the request is limited, 0 otherwise.
-- remaining: Available tokens after the current request.
-- reset_after: Time in seconds until rate limiter resets(string to preserve precision).
-- retry_after: Time in seconds until the request is allowed(string to preserve precision).
return {limited, remaining, tostring(reset_after), tostring(retry_after)}
