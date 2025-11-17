-- Leaking bucket based on [As a meter](https://en.wikipedia.org/wiki/Leaky_bucket).
-- ARGV[1]: rate - Leak rate (requests processed per second).
-- ARGV[2]: capacity - Maximum capacity of the bucket.
-- ARGV[3]: cost - Weight of current request.
-- KEYS[1]: Redis hash key storing bucket state.

local rate = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local cost = tonumber(ARGV[3])
local now = tonumber(redis.call("TIME")[1])

-- Start with empty bucket.
local last_tokens = 0
-- Initialize last leak time.
local last_refreshed = now
-- Get stored bucket state from Redis
local bucket = redis.call("HMGET", KEYS[1], "tokens", "last_refreshed")

-- Override defaults if bucket exists.
if bucket[1] ~= false then
    last_tokens = tonumber(bucket[1])
    last_refreshed = tonumber(bucket[2])
end

-- Calculate time elapsed since last leak.
local time_elapsed = math.max(0, now - last_refreshed)
-- Calculate new water level(leak over time).
local tokens = math.max(0, last_tokens - (math.floor(time_elapsed * rate)))

-- Check if request exceeds available water level.
local limited = tokens + cost > capacity
if limited then
    return {limited, capacity - tokens}
end

-- Time to empty full bucket.
local fill_time = capacity / rate
-- Set expiration to prevent stale data.
redis.call("EXPIRE", KEYS[1], math.floor(2 * fill_time))
-- Store new water level and update timestamp.
redis.call("HSET", KEYS[1], "tokens", tokens + cost, "last_refreshed", now)

-- Return [limited, remaining]
-- limited: 1 if over limit, 0 otherwise.
-- remaining: available capacity after processing request.
return {limited, capacity - (tokens + cost)}
