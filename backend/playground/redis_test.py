import redis

r = redis.Redis(
    host='redis-14324.c15.us-east-1-4.ec2.cloud.redislabs.com',
    port=14324,
    decode_responses=True,
    username="default",
    password="8MpHv6o4C1nffvl2jMu060SMI9usS7Yr",
)

success = r.set('foo', 'bar')
# True

result = r.get('foo')
print(result)
