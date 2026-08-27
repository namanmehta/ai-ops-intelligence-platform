import os

import mlflow
import json
from orchestrator_agent import run_orchestrator, client

os.environ["DATABRICKS_HOST"] = f"https://{os.getenv('DATABRICKS_SERVER_HOSTNAME')}"
os.environ["DATABRICKS_TOKEN"] = os.getenv("DATABRICKS_ACCESS_TOKEN")

mlflow.set_tracking_uri("databricks")
mlflow.set_experiment("/Shared/ai_ops_eval")

TEST_CASES = [
    {
        "id": "retry_storm",
        "task": "Investigate pl_payments_bronze_silver's recent run history for any issues.",
        "expected_finding": "The pipeline had a run with 17 retries and took about 2.5 hours, breaching its 20-minute SLA."
    },
    {
        "id": "schema_drift",
        "task": "Check the payments pipeline for any recent schema changes.",
        "expected_finding": "A new field called gateway_ref was added to the payments data, and it was handled as an additive, non-breaking change."
    },
    {
        "id": "row_count_drop",
        "task": "Check pl_orders_bronze_silver for any unusual drop in output row counts compared to input.",
        "expected_finding": "A run processed 5,100 input rows but only output 1,780 rows, roughly a 65% loss."
    },
    {
        "id": "null_explosion",
        "task": "Check the amount column in payments for data quality issues over the last 14 days, table payments, column amount, timestamp column processed_at.",
        "expected_finding": "August 1st had an unusually high null rate (around 28%) in the amount column compared to 0% on other days."
    },
    {
        "id": "duplicate_records",
        "task": "Check if there are any duplicate payment records and whether this has happened before.",
        "expected_finding": "There are duplicate payment_id values, roughly 50 payments appearing twice."
    },
]

JUDGE_SYSTEM_PROMPT = """You are grading whether an AI system's investigation report
correctly identified a known finding. You will be given the expected finding and the
system's actual report. Respond with exactly one word, PASS or FAIL, followed by a
one-sentence reason. PASS means the report clearly identifies the same core fact as
the expected finding, even if worded differently. FAIL means it missed it, got it
wrong, or is too vague to count."""

def judge(expected_finding: str, actual_report: str) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=200,
        system=JUDGE_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Expected finding: {expected_finding}\n\nActual report:\n{actual_report}"
        }]
    )
    return response.content[0].text

def run_eval():
    with mlflow.start_run():
        results = []
        for case in TEST_CASES:
            print(f"\nRunning: {case['id']}")
            report = run_orchestrator([{"role": "user", "content": case["task"]}])
            verdict = judge(case["expected_finding"], report)
            passed = verdict.strip().upper().startswith("PASS")
            results.append({"id": case["id"], "passed": passed, "verdict": verdict})
            print(f"  {verdict}")

            mlflow.log_metric(f"{case['id']}_passed", 1 if passed else 0)
            mlflow.log_text(verdict, f"{case['id']}_verdict.txt")
            mlflow.log_text(report, f"{case['id']}_report.txt")

        passed_count = sum(1 for r in results if r["passed"])
        pass_rate = passed_count / len(results)

        mlflow.log_metric("pass_rate", pass_rate)
        mlflow.log_metric("passed_count", passed_count)
        mlflow.log_metric("total_cases", len(results))

        print(f"\n=== {passed_count}/{len(results)} passed ===")
        return results

if __name__ == "__main__":
    run_eval()