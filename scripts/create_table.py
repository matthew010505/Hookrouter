import os
from dotenv import load_dotenv
import clickhouse_connect

# Load .env variables
load_dotenv()

# Initialize ClickHouse client
client = clickhouse_connect.get_client(
    host=os.getenv("CLICKHOUSE_HOST"),
    user=os.getenv("CLICKHOUSE_USER"),
    password=os.getenv("CLICKHOUSE_PASSWORD"),
    secure=True
)

# Create table SQL
create_table_sql = """
CREATE TABLE IF NOT EXISTS Urldata1 (
    u_id UUID,
    url String,
    secret String
) ENGINE = MergeTree()
ORDER BY u_id
"""

# Execute
client.command(create_table_sql)
print("✅ Table 'Urldata1' created (if it did not exist).")
