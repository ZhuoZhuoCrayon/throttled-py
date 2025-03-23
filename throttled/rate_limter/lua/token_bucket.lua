-- Token Bucket algorithm implementation for rate limiting.
-- ARGV[1]: rate - Tokens generated per second
-- ARGV[2]: capacity - Maximum number of tokens the bucket can hold.
-- ARGV[3]: cost - Number of tokens required for the current request.
-- ARGV[4]: now - Current time in seconds.
-- KEYS[1]: Redis hash key storing bucket state.

local rate = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local cost = tonumber(ARGV[3])
local now = tonumber(ARGV[4])

-- Initialize default bucket state.
local last_tokens = capacity    -- Start with full bucket.
local last_refreshed = now      -- Initialize last refresh time.
-- Get stored bucket state from Redis
local bucket = redis.call("HMGET", KEYS[1], "tokens", "last_refreshed")

-- Override default bucket state with stored state.
if bucket[1] ~= false then
    last_tokens = tonumber(bucket[1])
    last_refreshed = tonumber(bucket[2])
end

-- Calculate time elapsed since last refresh.
local time_elapsed = math.max(0, now - last_refreshed)
-- Calculate new tokens based on time elapsed.
local tokens = math.min(capacity, last_tokens + (math.floor(time_elapsed * rate)))

-- Check if request exceeds available tokens.
local limited = cost > tokens
if limited then
    return {limited, tokens}
end

-- Deduct tokens for current request.
tokens = tokens - cost
-- Calculate time to refill bucket.
local fill_time = capacity / rate
-- Update bucket state in Redis.
redis.call("HSET", KEYS[1], "tokens", tokens, "last_refreshed", now)
redis.call("EXPIRE", KEYS[1], math.floor(2 * fill_time))

-- Return [limited, tokens]
-- limited: 1 if over limit, 0 otherwise.
-- tokens: number of tokens remaining in bucket.
return {limited, tokens}
