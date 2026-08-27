import os
import requests
from dotenv import load_dotenv
from databricks import sql

load_dotenv()

def get_pipeline_logs(pipeline_id: str, limit: int = 5):
    connection = sql.connect(
        server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=os.getenv("DATABRICKS_ACCESS_TOKEN"),
    )
    cursor = connection.cursor()
    cursor.execute(f"""
        SELECT run_id, started_at, completed_at, status,
               row_count_in, row_count_out, retry_count, error_message
        FROM ai_ops_platform.bronze.pipeline_runs
        WHERE pipeline_id = '{pipeline_id}'
        ORDER BY started_at DESC
        LIMIT {limit}
    """)
    columns = [desc[0] for desc in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    cursor.close()
    connection.close()
    return rows

def list_pipelines():
    connection = sql.connect(
        server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=os.getenv("DATABRICKS_ACCESS_TOKEN"),
    )
    cursor = connection.cursor()
    cursor.execute("SELECT pipeline_id, pipeline_name, sla_minutes FROM ai_ops_platform.bronze.pipeline_metadata")
    columns = [desc[0] for desc in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    cursor.close()
    connection.close()
    return rows

def query_incident_history(query_text: str, num_results: int = 3):
    host = os.getenv("DATABRICKS_SERVER_HOSTNAME")
    token = os.getenv("DATABRICKS_ACCESS_TOKEN")

    url = f"https://{host}/api/2.0/vector-search/indexes/ai_ops_platform.bronze.incident_history_index_v3/query"
    headers = {"Authorization": f"Bearer {token}"}
    body = {
        "query_text": query_text,
        "columns": ["description", "incident_id", "root_cause", "resolution"],
        "num_results": num_results,
        "query_type": "HYBRID"
    }

    response = requests.post(url, headers=headers, json=body)
    data = response.json()

    columns = [c["name"] for c in data["manifest"]["columns"]]
    rows = [dict(zip(columns, row)) for row in data["result"]["data_array"]]
    return rows

def query_documentation(query_text: str, num_results: int = 3):
    host = os.getenv("DATABRICKS_SERVER_HOSTNAME")
    token = os.getenv("DATABRICKS_ACCESS_TOKEN")

    url = f"https://{host}/api/2.0/vector-search/indexes/ai_ops_platform.bronze.doc_index_2/query"
    headers = {"Authorization": f"Bearer {token}"}
    body = {
        "query_text": query_text,
        "columns": ["content", "doc_id"],
        "num_results": num_results,
        "query_type": "HYBRID"
    }

    response = requests.post(url, headers=headers, json=body)
    data = response.json()

    columns = [c["name"] for c in data["manifest"]["columns"]]
    rows = [dict(zip(columns, row)) for row in data["result"]["data_array"]]
    return rows

def get_data_quality_results(table_name: str, limit: int = 5):
    connection = sql.connect(
        server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=os.getenv("DATABRICKS_ACCESS_TOKEN"),
    )
    cursor = connection.cursor()
    cursor.execute(f"""
        SELECT check_id, run_id, table_name, check_type,
               expected_value, actual_value, passed, checked_at
        FROM ai_ops_platform.bronze.data_quality_results
        WHERE table_name = '{table_name}'
        ORDER BY checked_at DESC
        LIMIT {limit}
    """)
    columns = [desc[0] for desc in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    cursor.close()
    connection.close()
    return rows

def check_daily_null_rate(table_name: str, column_name: str, date_column: str, days: int = 14):
    connection = sql.connect(
        server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=os.getenv("DATABRICKS_ACCESS_TOKEN"),
    )
    cursor = connection.cursor()
    cursor.execute(f"""
        SELECT
            DATE({date_column}) AS day,
            COUNT(*) AS total_rows,
            SUM(CASE WHEN {column_name} IS NULL THEN 1 ELSE 0 END) AS null_rows
        FROM ai_ops_platform.bronze.{table_name}
        GROUP BY DATE({date_column})
        ORDER BY day DESC
        LIMIT {days}
    """)
    columns = [desc[0] for desc in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    cursor.close()
    connection.close()

    for r in rows:
        r["null_rate_percent"] = round((r["null_rows"] / r["total_rows"]) * 100, 2) if r["total_rows"] else 0

    return rows

from datetime import datetime

# --- Guardrail: only these pipeline_ids are allowed to have incidents written against them.
# Verify this list against `SELECT DISTINCT pipeline_id FROM ai_ops_platform.bronze.pipeline_metadata`
# and add any that are missing before testing.
KNOWN_PIPELINE_IDS = {
    "pl_orders_bronze_silver",
    "pl_payments_bronze_silver",
}

MIN_FIELD_LENGTH = 20

def write_incident(pipeline_id, title, description, root_cause, resolution):
    if pipeline_id not in KNOWN_PIPELINE_IDS:
        return {
            "error": f"'{pipeline_id}' is not a recognized pipeline_id. "
                     f"Known pipelines are: {', '.join(sorted(KNOWN_PIPELINE_IDS))}."
        }

    for field_name, value in [
        ("title", title),
        ("description", description),
        ("root_cause", root_cause),
        ("resolution", resolution),
    ]:
        if not value or len(value.strip()) < MIN_FIELD_LENGTH:
            return {
                "error": f"'{field_name}' is missing or too short to be a real incident record "
                         f"(needs at least {MIN_FIELD_LENGTH} characters)."
            }

    def escape(text):
        return text.replace("'", "''")

    connection = sql.connect(
        server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=os.getenv("DATABRICKS_ACCESS_TOKEN"),
    )
    cursor = connection.cursor()

    cursor.execute("""
        SELECT incident_id FROM ai_ops_platform.bronze.incident_history
        ORDER BY incident_id DESC LIMIT 1
    """)
    last_id = cursor.fetchone()[0]
    next_number = int(last_id.split("-")[1]) + 1
    new_incident_id = f"INC-{next_number}"

    now = datetime.now()

    cursor.execute(f"""
        INSERT INTO ai_ops_platform.bronze.incident_history
        (incident_id, pipeline_id, title, description, root_cause, resolution, detected_at, resolved_at, recovery_minutes)
        VALUES (
            '{new_incident_id}',
            '{escape(pipeline_id)}',
            '{escape(title)}',
            '{escape(description)}',
            '{escape(root_cause)}',
            '{escape(resolution)}',
            '{now}',
            '{now}',
            0
        )
    """)

    cursor.close()
    connection.close()

    return {"incident_id": new_incident_id, "status": "saved"}

# --- Guardrail: propose_remediation may only ever record one of these operational actions,
# regardless of what the model tries to pass in.
ALLOWED_REMEDIATION_ACTIONS = {"retry", "pause", "alert_oncall"}

REMEDIATION_PROPOSALS = []

def propose_remediation(pipeline_id: str, action: str, reason: str):
    if action not in ALLOWED_REMEDIATION_ACTIONS:
        return {
            "error": f"'{action}' is not an allowed remediation action. "
                     f"Allowed actions are: {', '.join(sorted(ALLOWED_REMEDIATION_ACTIONS))}."
        }

    proposal_id = f"REM-{len(REMEDIATION_PROPOSALS) + 1:03d}"
    proposal = {
        "proposal_id": proposal_id,
        "pipeline_id": pipeline_id,
        "action": action,
        "reason": reason,
        "status": "pending"
    }
    REMEDIATION_PROPOSALS.append(proposal)
    return proposal

if __name__ == "__main__":
    results = check_daily_null_rate("payments", "amount", "processed_at")
    for r in results:
        print(r)