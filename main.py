from fastapi import FastAPI, HTTPException, status, Response, Header, Request
from pydantic import BaseModel
import redis
from rq import Queue, Retry
import logging
import json
import hmac
import hashlib
import uuid
import os

# Environment-based Redis connections
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_conn = redis.from_url(REDIS_URL)
delivery_log_store = redis.from_url(os.getenv("DELIVERY_LOG_URL", REDIS_URL.replace("/0", "/2")))
cache = redis.from_url(os.getenv("CACHE_URL", REDIS_URL.replace("/0", "/1")))

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Subscription imports
from api.subscriptions import (
    insert_urldata,
    get_urldata_by_id,
    update_urldata_url,
    delete_urldata,
    UrlData,
    UrlUpdate,
)

# RQ Queue
queue = Queue("webhooks", connection=redis_conn)

# FastAPI app initialization
app = FastAPI()


# CRUD Endpoints
@app.post("/urldata/", status_code=201)
async def create_urldata_endpoint(item: UrlData):
    return insert_urldata(item)

@app.get("/urldata/{u_id}", response_model=UrlData)
async def read_urldata_endpoint(u_id: str):
    return get_urldata_by_id(u_id)

@app.put("/urldata/{u_id}", response_model=UrlData)
async def modify_urldata_endpoint(u_id: str, payload: UrlUpdate):
    return update_urldata_url(u_id, payload.new_url)

@app.delete("/urldata/{u_id}", status_code=200)
async def remove_urldata_endpoint(u_id: str):
    return delete_urldata(u_id)

# Webhook Payload Model
class WebhookPayload(BaseModel):
    event: str
    data: dict

# Ingest Webhook
@app.post("/ingest/{subscription_id}", status_code=status.HTTP_202_ACCEPTED)
async def ingest_webhook(
    subscription_id: str,
    payload: WebhookPayload,
    request: Request,
    x_hub_signature_256: str = Header(None)
):
    raw_body = json.dumps(await request.json(), separators=(",", ":")).encode()

    logger.info("raw", raw_body)

    # Cache lookup
    cache_key = f"subscription:{subscription_id}"
    sub = None
    try:
        raw = cache.get(cache_key)
        if raw:
            sub = json.loads(raw)
            logger.info("Cache hit for %s", subscription_id)
    except Exception:
        logger.warning("Cache lookup error for %s", subscription_id)

    if sub is None:
        sub = get_urldata_by_id(subscription_id)
        try:
            cache.set(cache_key, json.dumps(sub), ex=300)
            logger.info("Cached subscription %s", subscription_id)
        except Exception:
            logger.warning("Cache set error for %s", subscription_id)

    # Signature verification
    secret = sub.get("secret")
    if not secret:
        raise HTTPException(status_code=400, detail="Missing secret")

    expected_signature = hmac.new(
        key=secret.encode(),
        msg=raw_body,
        digestmod=hashlib.sha256
    ).hexdigest()
    expected_header = f"sha256={expected_signature}"
    logger.info(expected_header)

    if not hmac.compare_digest(expected_header, x_hub_signature_256 or ""):
        raise HTTPException(status_code=403, detail="Invalid signature")

    delivery_id = str(uuid.uuid4())
    payload_dict = payload.dict()
    payload_dict["delivery_id"] = delivery_id

    queue.enqueue(
        "tasks.deliver_webhook",
        kwargs={
            "subscription_id": subscription_id,
            "payload": payload_dict,
            "attempt_number": 1
        },
        retry=Retry(max=5, interval=[10, 30, 60, 300, 900])
    )

    return {"status": "accepted", "delivery_id": delivery_id}

# Delivery Status Endpoint
@app.get("/status/delivery/{delivery_id}")
def get_delivery_status(delivery_id: str):
    key = f"delivery:{delivery_id}"
    entries = delivery_log_store.lrange(key, 0, -1)
    if not entries:
        raise HTTPException(status_code=404, detail="No logs for delivery ID")
    return [json.loads(e) for e in entries]

# Subscription Logs Endpoint
@app.get("/status/subscription/{subscription_id}")
def get_subscription_logs(subscription_id: str):
    key = f"subscription:{subscription_id}:logs"
    entries = delivery_log_store.lrange(key, -20, -1)
    if not entries:
        raise HTTPException(status_code=404, detail="No logs for subscription")
    return [json.loads(e) for e in entries]

# Test Webhook Receiver
@app.post("/point1", status_code=status.HTTP_202_ACCEPTED)
async def receive_webhook_payload(payload: WebhookPayload):
    logger.info("At point1 received: %s", payload.json())
    return Response(status_code=status.HTTP_202_ACCEPTED)


@app.get("/status/logs/all")
def get_all_logs():
    keys = delivery_log_store.keys("delivery:*") + delivery_log_store.keys("subscription:*:logs")
    all_logs = {}
    
    for key in keys:
        entries = delivery_log_store.lrange(key, 0, -1)
        decoded_entries = [json.loads(e) for e in entries]
        all_logs[key.decode() if isinstance(key, bytes) else key] = decoded_entries

    if not all_logs:
        raise HTTPException(status_code=404, detail="No logs found")
    return all_logs
