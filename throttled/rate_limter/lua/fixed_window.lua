local period = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local cost = tonumber(ARGV[3])
local current = redis.call("INCRBY", KEYS[1], cost)

if current == cost then
    redis.call("EXPIRE", KEYS[1], period)
end

return {current > limit and 1 or 0, current}
