import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic
from investigator_agent import run_investigator
from knowledge_agent import run_knowledge_agent
from data_quality_agent import run_data_quality_agent
from tools import write_incident, propose_remediation

load_dotenv()

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

AVAILABLE_TOOLS = {
    "run_investigator": run_investigator,
    "run_knowledge_agent": run_knowledge_agent,
    "run_data_quality_agent": run_data_quality_agent,
    "write_incident": write_incident,
    "propose_remediation": propose_remediation,
}

SYSTEM_PROMPT = """You are an orchestrator investigating data pipeline incidents.

Once you have concluded an investigation and have a clear title, description,
root cause, and resolution or recommendation, call write_incident to save it
to the incident history before giving your final answer to the user. Only do
this once you've actually reached a conclusion, not for simple questions that
don't involve investigating a real issue.

If your investigation concludes that a specific operational action would help
(retrying a failed pipeline run, pausing a pipeline, or alerting the on-call
team), call propose_remediation to record that as a proposal. You must never
claim the action has actually happened, since you only ever propose it, a
human has to separately approve it before anything real occurs. Only propose
operational actions like retry, pause, or alert, never propose or make source
code changes."""

tools = [
    {
        "name": "run_investigator",
        "description": "Investigate pipeline run history and logs to diagnose operational issues like failures, retries, schema changes, or missing runs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "What to investigate, in plain English"}
            },
            "required": ["task"]
        }
    },
    {
        "name": "run_knowledge_agent",
        "description": "Search past resolved incidents and documentation for similar cases and how they were fixed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "The symptom or question to search past incidents for"}
            },
            "required": ["task"]
        }
    },
    {
        "name": "run_data_quality_agent",
        "description": "Check data quality of specific tables/columns, like null rates, for anomalies.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "What data quality check to run, in plain English"}
            },
            "required": ["task"]
        }
    },
    {
        "name": "write_incident",
        "description": "Save a concluded investigation as a new incident in incident history, so future investigations can find it. Only call this once you have a real conclusion.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pipeline_id": {"type": "string", "description": "The pipeline this incident relates to"},
                "title": {"type": "string", "description": "Short title for the incident"},
                "description": {"type": "string", "description": "What happened, in a sentence or two"},
                "root_cause": {"type": "string", "description": "What actually caused it"},
                "resolution": {"type": "string", "description": "How it was or should be resolved"}
            },
            "required": ["pipeline_id", "title", "description", "root_cause", "resolution"]
        }
    },
    {
        "name": "propose_remediation",
        "description": "Propose a specific operational action to fix or mitigate an issue. This does NOT execute the action, it only records a proposal a human must approve. Only use for operational actions: retry, pause, or alert.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pipeline_id": {"type": "string", "description": "The pipeline this action applies to"},
                "action": {"type": "string", "description": "The action being proposed, e.g. retry, pause, or alert_oncall"},
                "reason": {"type": "string", "description": "Why this action is recommended"}
            },
            "required": ["pipeline_id", "action", "reason"]
        }
    }
]

def run_orchestrator(messages: list) -> str:
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages
        )

        if response.stop_reason != "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            return response.content[0].text

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"\nOrchestrator is calling: {block.name} with input: {block.input}")
                function = AVAILABLE_TOOLS[block.name]
                try:
                    result = function(**block.input)
                except Exception as e:
                    result = {"error": f"Tool call failed: {str(e)}"}
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, default=str)
                })

        messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    task = "We think something is wrong with our payments pipeline (table: payments, key column: amount, timestamp column: processed_at). Investigate what's going on, check if the amount column data itself looks healthy over the last 14 days, and tell me if anything like this has happened before."
    print("\n--- Orchestrator's final report ---")
    print(run_orchestrator([{"role": "user", "content": task}]))