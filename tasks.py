import logging
import requests
import redis
import json
import os
import datetime
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_conn = redis.from_url(REDIS_URL)
delivery_log_store = redis.from_url(os.getenv("DELIVERY_LOG_URL", REDIS_URL.replace("/0","/2")))
cache = redis.from_url(os.getenv("CACHE_URL", REDIS_URL.replace("/0","/1")))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

log_store = delivery_log_store

def log_delivery_attempt(log_data: dict):
    log_data["timestamp"] = datetime.datetime.utcnow().isoformat()
    key_by_delivery = f"delivery:{log_data['delivery_id']}"
    key_by_subscription = f"subscription:{log_data['subscription_id']}:logs"

    log_store.rpush(key_by_delivery, json.dumps(log_data))
    log_store.rpush(key_by_subscription, json.dumps(log_data))
    log_store.expire(key_by_delivery, 72 * 3600)
    log_store.expire(key_by_subscription, 72 * 3600)

def deliver_webhook(subscription_id: str, payload: dict, attempt_number: int = 1):
    from api.subscriptions import get_urldata_by_id

    delivery_id = payload.get("delivery_id", "unknown")
    try:
        record = get_urldata_by_id(subscription_id)
        callback_url = record["url"]
    except Exception as e:
        log_delivery_attempt({
            "delivery_id": delivery_id,
            "subscription_id": subscription_id,
            "attempt": attempt_number,
            "target_url": "N/A",
            "outcome": "Failure",
            "error": f"Subscription lookup failed: {e}"
        })
        return

    try:
        resp = requests.post(callback_url, json=payload, timeout=5)
        resp.raise_for_status()
        log_delivery_attempt({
            "delivery_id": delivery_id,
            "subscription_id": subscription_id,
            "attempt": attempt_number,
            "target_url": callback_url,
            "outcome": "Success",
            "status_code": resp.status_code
        })
    except requests.HTTPError as e:
        log_delivery_attempt({
            "delivery_id": delivery_id,
            "subscription_id": subscription_id,
            "attempt": attempt_number,
            "target_url": callback_url,
            "outcome": "Failed Attempt" if 400 <= e.response.status_code < 500 else "Failure",
            "status_code": e.response.status_code,
            "error": str(e)
        })
        if 400 <= e.response.status_code < 500:
            return
        raise
    except Exception as e:
        log_delivery_attempt({
            "delivery_id": delivery_id,
            "subscription_id": subscription_id,
            "attempt": attempt_number,
            "target_url": callback_url,
            "outcome": "Failure",
            "error": str(e)
        })
        raise
