import redis

# Connect to the cache DB (db=1)
r = redis.Redis(host="localhost", port=6379, db=1)

print("Scanning for subscription keys…")
for key in r.scan_iter("subscription:*"):
    print(f"\nKey: {key.decode()}")
    data = r.hgetall(key)
    for field, val in data.items():
        print(f"  {field.decode()}: {val.decode()}")
