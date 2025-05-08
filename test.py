import hmac
import hashlib
import json

def generate_signature(secret: str, payload: dict) -> str:
    raw_body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    print(raw_body)
    signature = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return f"sha256={signature}"

payload = {
    "event": "string",
    "data": {
        "additionalProp1": {}
    }
}

secret = "secret"


print(generate_signature(secret, payload))
