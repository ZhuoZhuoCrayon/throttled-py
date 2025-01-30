local period = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local cost = tonumber(ARGV[3])
local now_ms = tonumber(ARGV[4])

local current = redis.call("INCRBY", KEYS[1], cost)
if current == cost then
    redis.call("EXPIRE", KEYS[1], 3 * period)
end

local previous = redis.call("GET", KEYS[2])
if previous == false then
    previous = 0
end

local period_ms = period * 1000
local current_proportion = (now_ms % period_ms) / period_ms
previous = math.floor((1 - current_proportion) * previous)
local used = previous + current

return {used > limit and 1 or 0, used}
