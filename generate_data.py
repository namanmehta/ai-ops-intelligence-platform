import os
import uuid
from datetime import datetime, timedelta
import random

from dotenv import load_dotenv
from databricks import sql
from faker import Faker

load_dotenv()
fake = Faker()

connection = sql.connect(
    server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
    http_path=os.getenv("DATABRICKS_HTTP_PATH"),
    access_token=os.getenv("DATABRICKS_ACCESS_TOKEN"),
)
cursor = connection.cursor()

NUM_CUSTOMERS = 500
REGIONS = ["Northeast", "Midwest", "South", "West"]
SEGMENTS = ["Retail", "Enterprise", "SMB"]

def random_signup_date():
    start = datetime(2023, 1, 1)
    end = datetime(2026, 8, 1)
    delta = end - start
    return (start + timedelta(days=random.randint(0, delta.days))).date()

rows = []
for _ in range(NUM_CUSTOMERS):
    customer_id = str(uuid.uuid4())
    name = fake.name()
    email = fake.unique.email()
    region = random.choice(REGIONS)
    segment = random.choice(SEGMENTS)
    signup_date = random_signup_date()
    rows.append((customer_id, name, email, region, segment, signup_date))

print(f"Generated {len(rows)} customer rows. Inserting into Databricks...")

insert_sql = """
    INSERT INTO ai_ops_platform.bronze.customers
    (customer_id, name, email, region, segment, signup_date, ingested_at)
    VALUES (?, ?, ?, ?, ?, ?, current_timestamp())
"""

for row in rows:
    cursor.execute(insert_sql, row)

print("Done. Verifying row count...")
cursor.execute("SELECT COUNT(*) FROM ai_ops_platform.bronze.customers")
print(cursor.fetchone())

cursor.close()
connection.close()