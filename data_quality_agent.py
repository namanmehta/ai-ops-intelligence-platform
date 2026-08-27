import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic
from tools import check_daily_null_rate

load_dotenv()

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

AVAILABLE_TOOLS = {
    "check_daily_null_rate": check_daily_null_rate,
}

tools = [
    {
        "name": "check_daily_null_rate",
        "description": "Check the null rate for a specific column, broken down day by day, to spot localized data quality spikes that an all-time average would hide.",
        "input_schema": {
            "type": "object",
            "properties": {
                "table_name": {"type": "string", "description": "Table name, e.g. payments"},
                "column_name": {"type": "string", "description": "Column to check, e.g. amount"},
                "date_column": {"type": "string", "description": "Timestamp column to group by day, e.g. processed_at"},
                "days": {"type": "integer", "description": "How many recent days to check"}
            },
            "required": ["table_name", "column_name", "date_column"]
        }
    }
]

def run_data_quality_agent(task: str) -> str:
    messages = [{"role": "user", "content": task}]

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1500,
            tools=tools,
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
    print(run_data_quality_agent("Check the amount column in payments for any data quality issues over the last 14 days."))