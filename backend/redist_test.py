import redis

# 1. Fill in your actual details here
REDIS_HOST = "redis-14324.c15.us-east-1-4.ec2.cloud.redislabs.com"
REDIS_PORT = 14324
REDIS_PASSWORD = "8MpHv6o4C1nffvl2jMu060SMI9usS7Yr" 

# 2. Create the connection with SSL enabled
r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    #ssl=True,               # <--- MANDATORY for Redis Cloud
    #ssl_cert_reqs=None,      # <--- Bypasses certificate verify issues
    decode_responses=True,
    socket_connect_timeout=5
)

# 3. Run the test
try:
    print(f"Connecting to {REDIS_HOST}...")
    if r.ping():
        print("✅ SUCCESS! Redis is connected and alive.")
except Exception as e:
    print(f"❌ CONNECTION FAILED: {e}")