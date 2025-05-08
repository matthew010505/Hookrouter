# 🚀 Webhook Delivery Service

A scalable, secure, and asynchronous webhook ingestion and delivery system built with **FastAPI**, **Redis**, **RQ**, and **ClickHouse**—all deployable via Docker.

---

## 🌐 Live Application

Access the deployed service and interactive API docs at:  
http://16.170.210.14:8000/docs

---

## 📦 Project Structure

```
.
├── docker-compose.yml
├── Dockerfile
├── main.py
├── tasks.py
├── api/
│   └── subscriptions.py
├── scripts/
│   └── create_table.py
├── requirements.txt
└── README.md
```

- **FastAPI**: HTTP API + Swagger UI  
- **Redis**: caching + RQ job queue  
- **RQ**: background worker with retry logic  
- **ClickHouse Cloud**: column-oriented data store  
- **Docker Compose**: orchestrates `web`, `worker`, and `redis`

---

![image](https://github.com/user-attachments/assets/5168f6f2-9d5a-46d2-8fe1-eb0ac23f81b7)
![image](https://github.com/user-attachments/assets/3350a218-a2ff-4d93-8310-ecf82a4ffb13)



## ⚙️ Setup & Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/matthew010505/Hookrouter.git
cd Hookrouter/
```

### 2. Create your `.env` file

```bash
cat > .env <<EOF
CLICKHOUSE_HOST=<your-host>
CLICKHOUSE_USER=<your-user>
CLICKHOUSE_PASSWORD=<your-password>
EOF
```



#### 3. Create the ClickHouse table

1. **Log in** to your ClickHouse Cloud account.  
2. Click **Create Service** (or select your existing service).  
3. Click **Connect**.  
4. Select **Python** in the client dropdown.  
5. Copy the connection snippet and paste into your `.env` (we’ll reference these in code):

   ```python
   from clickhouse_connect import get_client

   client = get_client(
       host='YOUR_CLICKHOUSE_HOST',      # e.g. abc123.clickhouse.cloud
       port=8443,
       username='YOUR_USERNAME',
       password='YOUR_PASSWORD',
       secure=True
   )


Then execute the script below

```bash
cd scripts
python create_table.py
cd ..
```

### 4. Install Docker & Docker Compose

- **Docker Engine**  
  https://docs.docker.com/engine/install/

- **Compose V2 plugin**  
  ```bash
  sudo apt-get update
  sudo apt-get install docker-compose-plugin
  ```
  _or_  
  ```bash
  sudo apt-get install docker-compose
  ```

### 5. Build & run with Docker Compose

```bash
docker-compose up --build
```

Visit: http://localhost:8000/docs

---

## 🧪 API Endpoints & Sample `curl` Commands

1. **Create Subscription**  
   **POST** `/urldata/`  
   Request body:
   ```json
   {
     "url":    "https://your-callback.example.com/hook",
     "secret": "my-shared-secret"
   }
   ```
   ```bash
   curl -X POST http://16.170.210.14:8000/urldata/      -H "Content-Type: application/json"      -d '{"url":"https://…","secret":"…"}'
   ```

2. **Get Subscription**  
   **GET** `/urldata/{u_id}`  
   ```bash
   curl -X GET http://16.170.210.14:8000/urldata/{subscription_u_id}      -H "accept: application/json"
   ```

3. **Update Subscription URL**  
   **PUT** `/urldata/{u_id}`  
   Request body:
   ```json
   { "new_url": "https://new-callback.example.com/hook" }
   ```
   ```bash
   curl -X PUT http://16.170.210.14:8000/urldata/{subscription_u_id}      -H "Content-Type: application/json"      -d '{"new_url":"https://…"}'
   ```

4. **Delete Subscription**  
   **DELETE** `/urldata/{u_id}`  
   ```bash
   curl -X DELETE http://16.170.210.14:8000/urldata/{subscription_u_id}
   ```

5. **Ingest Webhook**  
   **POST** `/ingest/{subscription_id}`  
   Headers:
   ```
   x-hub-signature-256: sha256=<HMAC_HEX>
   ```
   Body:
   ```json
   {
     "event": "user.created",
     "data":  { "id": 123, "name":"Alice" }
   }
   ```
   ```bash
   curl -X POST http://16.170.210.14:8000/ingest/{subscription_id}      -H "Content-Type: application/json"      -H "x-hub-signature-256: sha256=<signature>"      -d '{"event":"…","data":{…}}'
   ```

6. **Get Delivery Status**  
   **GET** `/status/delivery/{delivery_id}`  
   ```bash
   curl -X GET http://16.170.210.14:8000/status/delivery/{delivery_id}
   ```

7. **Get Subscription Logs**  
   **GET** `/status/subscription/{subscription_id}`  
   ```bash
   curl -X GET http://16.170.210.14:8000/status/subscription/{subscription_id}
   ```

8. **Test Receiver (dev only)**  
   **POST** `/point1`  
   Use as a sample callback URL.

9. **Get All Logs**  
   **GET** `/status/logs/all`  
   ```bash
   curl -X GET http://localhost:8000/status/logs/all
   ```

---

## 🏗️ Architecture & Design

- **Framework**: FastAPI  
  - Async endpoints, automatic Swagger UI, Pydantic validation

- **Database**: ClickHouse Cloud  
  - Columnar `MergeTree` table `Urldata1(u_id, url, secret)`  
  - `ORDER BY u_id` for fast lookups

- **Queue & Cache**: Redis  
  - **RQ** for background jobs  
  - Retry: `Retry(max=5, interval=[10,30,60,300,900])`  
  - Cache subscription data (TTL 300s)

- **Worker**:  
  - Posts webhook to subscriber URL, logs attempts

---

## 💾 Database Schema & Indexing

```sql
CREATE TABLE Urldata1 (
  u_id   String,
  url    String,
  secret String
) ENGINE = MergeTree()
ORDER BY u_id;
```

---

## 💰 Cost Estimation (Free Tier)

| Component           | Specs             | Monthly Cost |
|---------------------|-------------------|--------------|
| EC2 `t3.micro`      | 1 vCPU, 1 GiB RAM | $0 (750h free) |
| Redis & RQ          | co-located        | $0            |
| ClickHouse Cloud FT | 10M inserts/month | $0            |
| EBS (30 GiB)        | gp2 SSD           | $0 (free)     |
| Bandwidth (180 MB)  | first 1 GB free   | $0            |

**Usage**:  
- 5000 webhooks/day → 150 K/month (<10 M)  
- ~3.5 inserts/min (limit = 231/min)  

**Total**: **$0.00 / month**

---


