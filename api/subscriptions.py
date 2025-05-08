import logging
from fastapi import HTTPException
from pydantic import BaseModel
import clickhouse_connect
import uuid
import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# ——— Logging setup ———
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s ─ %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ——— ClickHouse client ———
client = clickhouse_connect.get_client(
    host=os.getenv("CLICKHOUSE_HOST"),
    user=os.getenv("CLICKHOUSE_USER"),
    password=os.getenv("CLICKHOUSE_PASSWORD"),
    secure=True
)

# ——— Pydantic models ———
class UrlData(BaseModel):
    url: str
    secret: str

class UrlUpdate(BaseModel):
    new_url: str


def insert_urldata(item: UrlData) -> dict:
    """
    Inserts a new row into Urldata1 if not already present.
    Raises HTTPException(409) if record exists, or 500 on other failures.
    """
    # 1) Existence check
    u_id=str(uuid.uuid4())
    count_query = f"SELECT count() FROM Urldata1 WHERE u_id = '{u_id}'"
    try:
        result = client.query(count_query)
        count = result.result_rows[0][0]
        if count > 0:
            # Conflict
            raise HTTPException(status_code=409, detail="Record already exists")
    except HTTPException:
        # Pass through 409
        raise
    except Exception:
        logger.exception("Error checking existence in Urldata1")
        raise HTTPException(status_code=500, detail="Existence check failed")

    # 2) Insert new record
    record = [[u_id, item.url, item.secret]]
    try:
        client.insert('Urldata1', record)
        logger.info("Successfully inserted URL: %s", item.url)
        return {
            "u_id": u_id,
            "url": item.url,
            "secret": item.secret
        }
    except Exception:
        logger.exception("Error inserting into Urldata1")
        raise HTTPException(status_code=500, detail="Insertion failed")


def get_urldata_by_id(u_id: str) -> dict:
    """
    Fetches a row from Urldata1 by u_id.
    Returns a dict if found, else HTTPException(404).
    """
    query = f"SELECT u_id, url, secret FROM Urldata1 WHERE u_id = '{u_id}'"
    try:
        result = client.query(query)
        rows = result.result_rows
        if not rows:
            raise HTTPException(status_code=404, detail="Record not found")
        u_id_val, url_val, secret_val = rows[0]
        return {"u_id": u_id_val, "url": url_val, "secret": secret_val}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error querying Urldata1")
        raise HTTPException(status_code=500, detail="Query failed")


def update_urldata_url(u_id: str, new_url: str) -> dict:
    """
    Updates the URL field of an existing Urldata1 record by u_id.
    Returns updated record or HTTPException.
    """
    # Ensure it exists
    data=get_urldata_by_id(u_id)

    sql = (
        "ALTER TABLE Urldata1 "
        f"UPDATE url = '{new_url}' WHERE u_id = '{u_id}'"
    )
    data["url"]=new_url
    try:
        client.command(sql)
        logger.info("Updated URL for u_id=%s to %s", u_id, new_url)
        return data
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error updating Urldata1")
        raise HTTPException(status_code=500, detail="Update failed")


def delete_urldata(u_id: str) -> dict:
    """
    Deletes a record from Urldata1 by u_id.
    Raises HTTPException(404) if not found.
    """
    # Ensure it exists
    get_urldata_by_id(u_id)

    sql = (
        "ALTER TABLE Urldata1 DELETE WHERE u_id = '{u_id}'".replace("{u_id}", u_id)
    )
    try:
        client.command(sql)
        logger.info("Deleted record u_id=%s", u_id)
        return {"message": "Deleted successfully"}
    except Exception:
        logger.exception("Error deleting from Urldata1")
        raise HTTPException(status_code=500, detail="Deletion failed")
