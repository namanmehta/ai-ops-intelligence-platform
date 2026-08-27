import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic
from tools import query_incident_history, query_documentation

load_dotenv()

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

AVAILABLE_TOOLS = {
    "query_incident_history": query_incident_history,
    "query_documentation": query_documentation,
}

tools = [
    {
        "name": "query_incident_history",
        "description": "Search past resolved incidents by meaning, using a natural language description of the current symptom. Returns similar past incidents with their root cause and resolution.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query_text": {"type": "string", "description": "A description of the current symptom or issue"},
                "num_results": {"type": "integer", "description": "How many similar past incidents to return"}
            },
            "required": ["query_text"]
        }
    },
    {
        "name": "query_documentation",
        "description": "Search internal documentation, runbooks, and data contracts by meaning. Use this for questions about policies, expected behavior, schema contracts, or how something is supposed to work, as opposed to past incidents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query_text": {"type": "string", "description": "What you're trying to find out from documentation"},
                "num_results": {"type": "integer", "description": "How many documentation results to return"}
            },
            "required": ["query_text"]
        }
    }
]

def run_knowledge_agent(task: str) -> str:
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
    print(run_knowledge_agent("What's our policy on schema changes, are new fields allowed to be added without breaking things?"))