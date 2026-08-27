import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic
from tools import get_pipeline_logs, list_pipelines

load_dotenv()

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

AVAILABLE_TOOLS = {
    "get_pipeline_logs": get_pipeline_logs,
    "list_pipelines": list_pipelines,
}

TOOLS_SCHEMA = [
    {
        "name": "list_pipelines",
        "description": "List all pipelines that exist, with their pipeline_id, name, and SLA.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_pipeline_logs",
        "description": "Get recent run history for a pipeline, including status, row counts, retries, and errors.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pipeline_id": {"type": "string", "description": "The pipeline ID, e.g. pl_orders_bronze_silver"},
                "limit": {"type": "integer", "description": "How many recent runs to fetch"}
            },
            "required": ["pipeline_id"]
        }
    }
]

def run_investigator(task: str) -> str:
    messages = [{"role": "user", "content": task}]

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1500,
            tools=TOOLS_SCHEMA,
            messages=messages
        )

        if response.stop_reason != "tool_use":
            return response.content[0].text

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
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
    print(run_investigator("Check all our pipelines and tell me if anything looks off."))