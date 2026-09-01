# AI Operations Intelligence Platform

A multi agent AI system that investigates data pipeline incidents automatically, built on Databricks, Python, and the Anthropic Claude API.

When a data pipeline fails or produces bad data, engineers typically spend hours manually correlating logs, schema history, data quality signals, and past incidents to find the root cause. This project builds an AI system that performs that investigation on its own, reasoning across live pipeline signals and a historical knowledge base to surface root causes in seconds.


<img width="947" height="383" alt="image" src="https://github.com/user-attachments/assets/c2fa7790-1536-4463-bf3b-9c747a144c2c" />

**Investigation in action**

<img width="935" height="457" alt="image" src="https://github.com/user-attachments/assets/407cda60-b4e9-464c-8a8c-bb2de3f899d2" />


**Evaluation tracking in MLflow**

<img width="903" height="398" alt="image" src="https://github.com/user-attachments/assets/92634571-1f33-4277-9de7-9d426e7f776e" />


## How it works

An orchestrator agent receives an incident description and coordinates three specialist agents to investigate it:

- **Investigator agent** pulls pipeline run logs and correlates them with schema changes to identify what actually broke and when.
- **Data quality agent** checks validation results and anomaly signals (null rates, row count drops, duplicate records) against expected thresholds.
- **Knowledge agent** retrieves similar past incidents and relevant documentation using RAG and Databricks Vector Search, so the investigation is grounded in real historical context instead of guessing.

All three agents share conversation memory across the investigation and communicate through explicit tool calls rather than free text, so every step of the reasoning is inspectable.

## Guardrails

Every action the system can take runs through code level checks, not just prompt instructions:

- Remediation actions (retry, pause, alert on call) are restricted to a hard coded allowlist. Anything outside that list is rejected before it reaches execution.
- Incident write backs are validated for a known pipeline ID and minimum field length before being committed, so the knowledge base cannot be polluted with malformed records.
- No remediation action executes without explicit human approval.

## Evaluation and observability

The system is graded against a benchmark of known incident scenarios (schema drift, duplicate records, row count drops, null explosions, retry storms) using an LLM as judge to score root cause accuracy. Current benchmark result: 80% (4 of 5) root cause accuracy.

Every evaluation run is tracked in MLflow, logging pass/fail per scenario, the full generated investigation report, and the judge's verdict as artifacts, so results are reproducible and comparable across runs rather than eyeballed from a chat transcript.

## Data platform

The project runs on its own synthetic enterprise data platform inside a dedicated Unity Catalog catalog (`ai_ops_platform`), built through a Bronze, Silver, Gold medallion architecture on Delta Lake. Synthetic tables cover orders, customers, shipments, payments, pipeline run logs, data quality results, incident history, and documentation, with six failure types injected on demand to simulate realistic incidents.

## Tech stack

Python, Anthropic Claude API, Databricks, Delta Lake, Unity Catalog, Databricks Vector Search, MLflow, FastAPI, Streamlit.


## Running it locally

1. Clone the repo and install dependencies.
2. Copy `.env.example` to `.env` and fill in your Databricks and Anthropic credentials.
3. Start the FastAPI backend: `uvicorn app:app --reload`
4. Start the Streamlit UI: `streamlit run streamlit_app.py`
5. Run the evaluation suite: `python eval.py`

## Known limitations

This is an independent portfolio project, not a production deployment, and a few gaps are left intentionally documented rather than hidden:

- A duplicate record detection tool is scoped but not yet built.
- Remediation proposals are held in memory for the current session rather than persisted.
- The MCP integration exists as a standalone proof of concept and is not wired into the main orchestrator.
- The system is not deployed; it runs locally against a live Databricks workspace.

## About

Built by Naman Mehta as an independent project to go deep on production grade AI engineering: tool calling, code level guardrails, retrieval grounded in real data, and an evaluation framework that reports the truth rather than a vibe.
