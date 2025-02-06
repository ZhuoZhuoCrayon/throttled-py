local rate = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local cost = tonumber(ARGV[3])
local now = tonumber(ARGV[4])

local last_tokens = capacity
local last_refreshed = now
local bucket = redis.call("HMGET", KEYS[1], "tokens", "last_refreshed")

if bucket[1] ~= false then
    last_tokens = tonumber(bucket[1])
    last_refreshed = tonumber(bucket[2])
end

local time_elapsed = math.max(0, now - last_refreshed)
local tokens = math.min(capacity, last_tokens + (math.floor(time_elapsed * rate)))

local limited = cost > tokens
if not limited then
    tokens = tokens - cost
end

local fill_time = capacity / rate
redis.call("HSET", KEYS[1], "tokens", tokens, "last_refreshed", now)
redis.call("EXPIRE", KEYS[1], math.floor(2 * fill_time))

return {limited, tokens}
